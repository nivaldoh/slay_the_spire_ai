# WH3 integration facts

Engine observations, API discrepancies and the route to investigate another capability.
Unless explicitly tied to an [agreed check](../../AGENTS.md#verification-hard-rule), these
are observations from the cited probes, **unverified** under the owner's rule. A documented
method name alone establishes neither availability nor its effects in this build.
Evidence paths are under `runs/twwarhammer3/`; `bN`/`vN` names a [log.md](log.md) entry.

Keep interface definitions in their existing code references: `engine/mailbox.py` for
bridge files/observation fields, `protocol.py` for orders, `battle/setup.py` for scenario
fields, and `mod/script/_lib/mod/twwarhammer3_ui.lua` for immediate UI operations. The
frontend script adds scheduling; battle probes accept immediate operations only.

## Pins

Patch 9.0.4 (executable product/file version 9.0.4.0), Steam buildid 25961564,
`Warhammer3.exe` sha256
`9bd58c63bd7fc5c9909b3d3d9b6b7a6ae4eac784369bf91a9e53c3e9f42be496` (pinned in
`engine/runtime.py`). Steam completed this update on 2026-10-15; earlier trials used
9.0.3, build 4366297, Steam 25823491, executable hash
`518c4f292f275142df13b96b9db704a3db7b4870b2c519df83d850596ecc822a`. Their manifests retain
that build and the report keeps the conditions separate. Since 2026-10-18 another build
warns (`doctor` warnings, `deployment.steam_build_pinned` false) instead of blocking; the
owner decides whether to re-pin. Windows Python 3.13.1 at
`C:/Python313/python.exe`; `--stills`
needs Pillow there. Profile preferences when pinned: fullscreen 1920x1080, unit size 2
("large"), AI stats modifier 1.1, realism off, multithreaded model on. `doctor` reads them
from `%APPDATA%/The Creative Assembly/Warhammer3/scripts/preferences.script.txt`; a
declared scenario sets its own AI stats modifier in the lobby
([Lobby settings](#lobby-settings-and-declared-scenarios)).

## Packs and loading

- Database tables in `db.pack` are versioned binary tables; `scripts/wh3_db.py` decodes one
  with RPFM's schema (`schema_wh3.ron` from rpfm-schemas, downloaded outside the
  repository) and prints rows: unit costs and caps (`main_units_tables`), weapons
  (`melee_weapons_tables`: `damage`, `ap_damage`, `bonus_v_large`) and attributes
  (`land_units_tables.attribute_group` through `unit_attributes_to_groups_junctions_tables`).
  Checked 2026-10-15: each table decodes to its last byte, and `damage` plus `ap_damage`
  equals the battle's recorded `weapon_damage` (Knights of the Realm 40, Questing Knights
  52, Grail Knights 46, Halberdiers 28). Nothing decoded is committed.
- Vanilla packs are PFH5 (layout in the `engine/pack.py` docstring). Patch 9 vanilla
  entries are zstd frames, read through the `zstd` CLI. The mod pack is written
  uncompressed with a fixed timestamp, so its hash depends only on the sources.
- Launch route: `Warhammer3.exe twwarhammer3_mods.txt;` from the game folder, the list
  holding `add_working_directory "C:/wh3-agent/mods";` and `mod "twwarhammer3.pack";`.
  The main menu shows "(modded)". A direct launch works with Steam running
  (`steam_appid.txt` is in the game folder).
- Startup skip: `engine/startup.py` installs a separate type-4 (movie) PFH5 pack,
  `data/zzz_twwarhammer3_skip_intro.pack`, with 18 entries: the five startup movies and
  13 localized epilepsy warnings, each replaced by a 595-byte blank CA-VP8 from
  MIT-licensed
  [twpatcher](https://github.com/Frodo45127/twpatcher/blob/a5783c5803d08cc4d5cdc40c9411549a55001c60/src/games/mod.rs)
  (license and source hash in `src/twwarhammer3/assets/`). Movie packs load without a
  mod-list entry, so the skip applies to ordinary Steam launches too. `gam_int.ca_vp8` is
  not overridden: `fe_game_intro_video_enabled false` in the preferences disables its
  startup playback and keeps the cinematic viewer. Preparation refuses to write while WH3
  runs, preserves the other preference bytes and leaves matching files untouched;
  `doctor` and the deployment record show the pack hashes and the effective preference.
  It saved about 131 s to the main menu (log.md, "Automatic startup video skipping");
  the initial static loading splash remains. To reverse it, stop WH3, delete the pack
  from `data/` and set the preference back to `true`; the next project launch reinstalls
  both.
- `script/_lib/lib_header.lua` creates `core`, `bm` (battle) and `tm` (frontend), then
  requires `lib_mod_loader.lua`, which calls `core:load_mods("/script/_lib/mod/",
  "/script/battle/mod/")` in battle and `"/script/frontend/mod/"` in the frontend. Each
  `*.lua` runs at top level under `pcall` (no `execute_mods` outside campaign), once per
  frontend or battle load, and each load is logged in `<game>/lua_mod_log.txt` ("Mod
  [...] loaded successfully" or the error).
- In a campaign the loader also loads `/script/_lib/mod/` and, on the first tick, calls
  under `pcall` every global function named after a loaded file
  (`script/_lib/lib_mod_loader.lua`, `core_object:execute_mods` in `lib_core.lua`, read from
  the extracted game scripts). `twwarhammer3_imagery` is one, so an owner's campaign with
  our mod list runs it with the campaign context. A simulation under Lua 5.1 stops in
  `save()` on a nil battle id before any file opens; the game would log the error in
  `lua_mod_log.txt` and go on (2026-10-21; unverified live). Renaming that global so it no
  longer matches its file would keep the call out of campaigns.
- Lua 5.1 environment: `io.open` on absolute Windows paths, `os.remove` and `os.rename`
  work in both scripts, as do `tm:repeat_real_callback(fn, ms, name)` in the frontend and
  `bm:repeat_real_callback` in battle. There is no `math.huge`. `loadstring` chunks run in
  the global environment, without `bm`; the `lua` menu step gives them the mod's
  environment with `setfenv`.
- CA replaces `string.find` with a UTF-8 literal search documented with three arguments;
  stock Lua's pattern/fourth-argument form is `string.find_lua` (`lib_lua_extensions.lua`).
  A four-argument diagnostic search failed to recognize its error text in this review;
  its exact native behavior is unverified. Lupa's stock Lua does not model that override.
- The game ships its scripting documentation as HTML in `data.pack`
  (`documentation/script/battle/*.html`, `documentation/ui/documentation.html`) and its
  script libraries in `data_script.pack` (`script/_lib/lib_battle_manager.lua`, ...).
  `pack --extract PACK NAME > runs/twwarhammer3/vanilla/NAME` copies one entry into the
  ignored folder; they are proprietary and are the authoritative local reference.

## Frontend automation

- Main menu: `buttons_holder/button_battle`, then `battle_frame/button_practice_battle`
  opens Skirmish vs A.I. Setup waits up to 240 s for the first button. Map/type tabs,
  AI-slot controls and Start still use component clicks; race, faction, fixed recruitment,
  mounts, ranks and declared settings use the lobby contexts behind those controls.
- `find_uicomponent`, simulated clicks and the component tree work in the frontend.
  `menu --dump` records ids, visibility, state and text; use context queries for values.
  Entries outside scroll view can exist without reading as visible. A find with
  `timeout_ms` waits for visibility; an expression with `timeout_ms` retries its assertion.
- Slot targeting checks belong to the declared setup, not to a stored UI address. The
  lobby sorts recruited units by class; its unit context ids encode list positions and
  are not established stable identities through sorting. Mount immediately by original
  type; assign XP after recruitment by final type/occurrence and compare multiplicities.
- Fixed recruitment resolves `CcoMainUnitRecord.CustomBattlePermissionsContext(faction)`
  and calls the slot's `RecruitUnit(permission, isReserve)`. The banner faction and
  `recruitment_faction` can differ. `CanRecruitUnit` checks permission; affordability is
  separate: the game's cost-label predicate compares main-unit cost with
  `FundsRemaining(!isReserve || permission.IsGeneralUnit)`. Our harness refuses either
  failure before changing the roster. A listed card alone never proved availability.
- Autogenerate remains a UI action for random armies; unit caps must allow it. The game
  keeps the last races/map across launches, and battle type/AI slots between battles.
  Survival removes the enemy slot; setup therefore selects the mode and fixes slot count.
- A step's `when` is a condition, not a wait. False branches consume no extra polling
  intervals; actual actions retain one per callback and explicit waits retain their delay.
  Failures and completion carry the request id. The frontend unloads when battle loading
  starts, so `play` uses the first battle observation as its setup handoff. Use `play` for
  a complete launch; `menu` requires a completed probe sequence before returning success.

### Lobby settings and declared scenarios

- A declared scenario applies timer, funds, AI stat modifier, difficulty, unit scale and
  realism through `CcoFrontendRoot`'s `CustomBattleLobbyContext.SettingsContext`, then
  reads them back. These controls can persist into ordinary play. Difficulty is selected
  by record key, not its numeric value; the preference uses a different numeric enum.
- Unit-scale records have indices 0–3 (small/normal/large/ultra), whereas battle `UnitSize`
  uses factors .25/.5/.75/1. Realism has `ToggleRealismMode()` and `IsRealismMode`; toggle
  only when its readback differs. The earlier claim that the lobby could not set it was
  wrong. The native battle readbacks independently check scale/realism; selected difficulty
  does not establish AI behavior. Field and command definitions stay in `battle/setup.py`.
- Selecting difficulty also resets its default AI stat modifier (very hard reset 1.0 to
  1.1 in the integration check). Apply the declared modifier after selecting difficulty;
  checking each setter alone would miss this interaction.
- Custom funds are applied before recruiting or buying mounts/XP. The ordinary UI accepts
  5000–999999; out-of-range context commands must not be assumed to represent valid funds.
  The declared Herald rosters need more than default funds and use 30000.
- Army presets: `button_bar_parent/load_save_parent/button_save_preset` and
  `button_load_preset` are "Save army preset" and "Load army preset". Their API is
  `CustomBattleLobbyContext.ArmyPresetFileHandlerContext`:
  `SaveArmyPresetForPlayerSlot(name, slotContext)`, `ArmyPresetExists(name)`, and
  `ArmyPresetList(0).FirstContext(Name == name).LoadForPlayerSlot(slotContext)`.
  `play` saves fixed armies under `gameai-<digest>` and loads them on subsequent launches;
  the digest includes the army declaration, battle type, declared settings and installed
  Steam build. Autogenerated armies/pools are always rebuilt. The game stores these presets
  in its user profile; a missing preset is rebuilt. A mismatched preset stops setup; delete
  that named preset in the game's load panel to rebuild it. Rematches still use rematch.
- Experience: an army's `experience` maps zero-based recruitment indices to integer ranks
  0–9, e.g. `"experience": {"1": 3, "2": 9}`. Unspecified ranks are zero. On a selected
  recruited card, `xp_visibility_parent/button_upgrade_unit` and `button_downgrade_unit`
  call `CcoCustomBattleUnit.IncreaseExperience()` / `DecreaseExperience()`; readback is
  `ExperienceLevel`. XP costs funds. Setup stops if an increment/decrement is refused.
  `CanEverIncreaseExperience` and `CanIncreaseExperience` distinguish permanent/current
  eligibility. A positive Captain rank request was refused in this review; its cause and
  character XP remain unverified. The live fixture keeps its mounted Captains at rank zero.
  The lobby sorts by class, so XP assignment happens after recruitment and selects units by
  type and occurrence. Loaded armies are checked by type/rank multiplicities, including duplicate
  units; the battle checks private startup ranks too. Reinforcement XP is not configured.
  Repeatable live check: `uv run --locked python tests/twwarhammer3/check_wh3_army_setup.py
  --output runs/twwarhammer3/army-setup-check-<new-name>` (two launches, unpaused at 1x;
  saves, clears, restarts, loads, compares ranks and lobby/battle stats). Passed at `c768460`:
  eight units including a mounted lord and ranks 0/1/3/9. Swordsmen attack/defence matched
  exactly (32/35/41); leadership XP bonuses over rank zero matched (+3/+10), although all
  friendly units had a -4 battle leadership offset whose cause remains unverified.
  [Evidence](log.md#2026-10-19-saved-armies-and-experience-harness-b41).
- Extended integration check: add `--integration` to the command above. At `e32b1b5`,
  four launches passed with ten saved units, three mounts (including duplicate Captains),
  ranks 0/1/3/9, a seven-unit reserve pool and permission/funds refusals without mutation.
  It deliberately disturbed difficulty/scale/realism, reapplied declarations and compared
  lobby with battle startup, then restored the original settings. Cold/warm setup took
  40.2/32.2 s in this one pair; this does not establish a general speedup. Restart uses
  supervised shutdown. The disturbed settings did not survive that shutdown in this trial;
  persistence after graceful menu exit remains unverified.
  [Evidence and component checks](log.md#2026-10-20-ui-and-lobby-integration-harness-b42).
- Battle read-backs on `CcoBattleRoot` (`setup.check_battle`): `UnitSize` (0.75 on this
  profile), `IsRealismModeEnabled`, `PlayerAllianceContext.IsDefender`, and
  `ArmyList.JoinString("" + AiStatsModifier, ";")`, the modifier per army
  (`CcoBattleArmy.AiStatsModifier`; 1.1 read on both armies, which is the setting, not
  proof that both get bonuses). `WillWinOnTimeout`, `BalanceOfPowerPercent` (the HUD's
  balance bar; kept out of the observation) and an empty `BattleNameText` also read.
- What the modifier does: `CcoUiUnitStatRecord.PreviewAiStatModifierString(1.1)` reports
  +10% melee attack, defence and weapon damage and +8 leadership. Startup snapshots at
  5.2 s (1.0 against 1.1) changed all 12 AI unit entries and none of the 12 player
  entries: about +10% melee attack, defence, weapon damage and charge (integer rounding)
  and +8 leadership, for example Marauders 28→31 attack and 60→68 leadership. UI
  `CcoUnitStat.ValueBase` already includes these AI settings, although the UI
  documentation says it excludes modifiers; `Value` is the current stat and also
  includes active effects. The mod records both privately at startup
  (`reports/bench-b2-starting-base-stat-comparison.json`).

## Battle

First observed in `runs/twwarhammer3/battle/attack-m3-20261013` (Khorne against Dwarfs,
5 units each, "An Ogre's Folly"), extended in the capability probes
(`runs/twwarhammer3/capability-probes/`, v13 to b8).

### Loading, phases and control

- The mod loader runs the battle script once per battle load, after `bm` exists.
  `bm.battle:end_current_battle_phase()` ends deployment (about 4.7 s in), and the
  `Deployed` phase callback fires right after.
- `bm:modify_battle_speed(0, true)` stops model time: the `repeat_callback` tick stops
  while `repeat_real_callback` polling continues. The owner's rule is unpaused 1x, so the
  mod sets speed 1 at load and never pauses (the removed pause mode is in log.md, "Unpaused
  1x battles only").
- One `unitcontroller` per friendly unit (`army:create_unit_controller()`, `add_units`,
  `take_control`) applies the orders.
- The battle UI root holds `menu_bar`, `panel_manager` and `dialogue_box`. The battle
  script accepts immediate UI steps from `menu.json` (`menu --battle`). Frontend-only
  `when`, `wait_ms` and `timeout_ms` modifiers are rejected before any step executes.
  A required failure stops the sequence; optional failures continue diagnostics but
  still produce a failed request. Both consumers reject another job's requests.

### Units and axes

- The unit fields and visibility filter are specified in `engine/mailbox.py`; the
  following are observed engine quirks, rather than another field inventory.
- `is_cavalry()` and `is_artillery()` were false for Marauder Horsemen and the
  Skullcannon; the class comes from `unit_class()` (the land_units class, e.g. `art_fld`).
  Screamers have class `inf_mel` while `can_fly()` and `is_currently_flying()` are true,
  so the mod classes every flying unit except a lord as `flying`.
- A unit's `x`/`z` is `unit:position()`, documented as the centre of the unit's main squad.
  A unit split between two fights can switch main squad, so its position jumps between them
  (f4 moved about 200 m back and forth nine times in `bench-b13-v1b2-siege-flankers-sol61-20261016`).
- Axes: x east, z north; a bearing is 0 at +z, clockwise (a unit at (-174, 34) facing 213
  was attacking an enemy at (-192, 13), bearing 221 from it).
- Walk/run speeds read the same way for visible enemies as for friendlies. They are
  capabilities, not measured velocities (Screamers 8.5/8.5 m/s, a Pegasus general
  10.5/10.5 m/s airborne).
- Specialist state: current and maximum barrier HP (separate from health), and per
  ability its cast range, radius and duration where the engine gives them (Rune ranges
  and nonzero Tzeentch barriers read live).

### Moves and attacks

- `goto_location`, `goto_location_angle_width(position, facing, width, run)` (forms up
  facing a bearing; a 20 m width read back as 20), `attack_unit(target, primary, run)`
  and `halt`. `goto_location_angle_width_q`, `goto_location_q` and `attack_unit_q` are
  native engine queues; two queued waypoints reached the second point.
- The formation centre can stop several metres from the ordered point: a short probe
  with a 5 m tolerance failed, a longer path with 15 m passed.
- `unit:can_reach_position(vector)` is false near the map edge and across terrain the
  unit cannot cross. After a refused move the mod tests 8 points at 16, then 32, then
  64 m with the unit's own query and reports the reachable ones; the engine itself
  sends no replacement order.
- The engine drops an attack when the target dies or leaves sight: the unit shows no
  `current_target`, `is_idle()` is true, and it stands until ordered again.
  `ordered_position()` is the unit's own position while it attacks (per the docs).
- An attack is `auto`, `ranged` or `melee`. An immediate melee attack by a missile unit
  selects its secondary attack (`attack_unit`'s primary flag false); units without
  missile range keep their primary melee attack. Queued attacks use `attack_unit_q` and
  its attack-method flag, so the mode does not change before the preceding move ends.
  Horsemen fired in ranged mode, then entered melee from a queued attack with 453
  ammunition left.
- Behaviour toggles: `can_use_behaviour` and `is_behaviour_active`. Fire-at-will,
  skirmish and guard (`defend`) toggled and read back on Khorne units;
  `change_formation_spacing` and `formed_attack` were unsupported there and are offered
  only where supported.

### Acknowledgements

Each acknowledgement result has a one-based `index`, `unit`, `ok` and `queued`. A failed
move rejects its queued successors (observed with an unreachable first point). An
acknowledgement reports a call issued to the engine, not visible execution; for native
queues `applied_ms` is the submission time, not the start of each step, and
`command_queue` is the last submitted sequence, its completion unconfirmed. Results from
before `863d10b` (2026-10-13) have no `index`.

### Abilities and magic

- Active ability keys come from `owned_non_passive_special_abilities` and are checked
  again at dispatch. `perform_special_ability(key)` without a unit raised `battle.unit
  expected, got no value` despite the documented optional target, so self abilities pass
  the caster. Foe Seeker raised the Herald's walk/run speeds from 1.9/4.8 to 2.4/6.0.
- `can_perform_special_ability` stays true after a cast: it is the engine's permission,
  not readiness. Readiness, cooldown, uses and magic cost come from the
  [UI context system](#ability-state-through-the-ui-context-system-probed-2026-10-13).
  The Winds of Magic pool and reserve are read from the player's army.
- Spells (`wizard-r3`, Balthasar Gelt in the Empire mirror): Glittering Robe on friendly
  swordsmen took the pool 12 → 7, Plague of Rust on visible infantry 11 → 7, ground
  Searing Doom 9 → 3. Back-to-back spell requests gave ambiguous pool changes, as a later
  command can interrupt an earlier cast, so probe casts separately. A unit ordering
  another unit's ability is refused by the dispatcher (`unavailable_ability`).
- Kairos's ground Pendulum (b7) was accepted at 64.6 s while the snapshot still showed 21
  magic and the spell ready; at 70.9 s the pool was 10 and the cooldown 39.8 s. Resources
  and readiness change after issuance, not in the acknowledging snapshot.
- The engine error "does not support this special ability" also appears when magic has
  fallen below the spell's cost by issuance (b4: 11 against 16, 9 against 12, after
  earlier spells took effect), so it does not by itself mean an unsupported spell
  (`reports/bench-b4-ground-refusal-resources.json`).
- Pool expenditure proves acceptance, not damage or a completed effect; damage
  attribution is unmeasured.

### Morale and flight

- `CcoBattleUnit` `MoralePercent` (the UI's leadership fraction, which can be negative:
  -2.506 for Kairos late in the b7 caster pilot) and `MoraleGreatestEffect` (for example
  "The enemy is in control of the battlefield - you must attack by land!" for flyers
  whose ground escorts died, or "Army losses").
- `CanToggleFlying`, `ToggleFlyingCooldownTimer` and `IsOrderable` read per unit;
  `ToggleFlying` is the player's flight command. The mod checks the unit's current state
  and availability before calling it. In `bench-b8-flight-probe-20261014`, landing
  grounded both flyers within 2.4 s, a repeated landing request during the cooldown left
  them grounded, and take-off after the cooldown made both airborne within 0.3 s
  (`reports/bench-b8-flight-acceptance.json`).

### Terrain

`bm.battle:battle_boundaries()` returns four corner vectors (±512 in x and z on the map
tested). The mod samples `get_terrain_height(x, z)` and `is_area_clear(vector, 0, 16,
16)` on a 32 m grid once at deployment: 1024 queries took 0.03 CPU s. This is a coarse
map of path restrictions, not unit-specific reachability: narrow crossings can lie
between samples and buildings can change later. River crossings, paths and walls are
otherwise not exposed (the chokepoint map has no buildings; its crossings are terrain).

### Result, timer and restart

- At `VictoryCountdown`, `battle_outcome_decided()`, `victorious_alliance()` and
  `local_alliance()` give the result ("lost" when the player's army broke).
- `remaining_conflict_time()` resets to -1 at `VictoryCountdown`. The mod keeps the last
  finite sample taken on engine ticks and infers expiry by comparing its deadline with
  the result time (observed on an isolated timer ending, b9). There is no end-cause
  getter, so combat and expiry in the same tick stay ambiguous.
- `bm:restart_battle()` (the `RestartBattle` context command on `CcoBattleRoot`) did
  nothing on the results screen. `bm:end_battle()` ends the victory countdown, the
  results popup's `in_battle_results_popup/.../button_rematch` asks "Are you sure you
  want to rematch this battle?", and `dialogue_box/both_group/button_tick` confirms; the
  same battle reloads in about 15 s with a fresh script environment and the same start.

## Ability state through the UI context system (probed 2026-10-13)

The script API has no getter for army abilities (army-wide abilities not owned by a unit,
such as Khorne's three kill unlocks) or for any ability's cooldown; the UI's context
system has both. Script reads it with `common.get_context_value(type, id, expression)`
and runs commands with `common.call_context_command(type, id, command)`; the UI context
documentation is `documentation/ui/documentation.html` in `data.pack`. Observed on
`kho5-dwf5` (`runs/twwarhammer3/probe-army-abilities-20261013/`, the mod.log of
`skills-v1.2-kho-20261013`):
- A unit's `CcoBattleUnit` id is its `unique_ui_id` as a string (1001, 1002, ... for the
  player's units).
- Expressions chain and concatenate: `BattleAbilityList.JoinString(SetupAbilityContext.RecordKey
  + "|" + CanCurrentlyPerform + "|" + RechargeTimeRemainingSecs, ";")` returned
  `wh_main_character_abilities_foe_seeker|true|0.00;...`. Booleans become `true`/`false`
  and floats two decimals. `Format("%S|%d", ...)` did not substitute.
- `BattleAbilityList` holds every ability with live state: `CanCurrentlyPerform`,
  `RechargeTimeRemainingSecs`, `RemainingUses` (-1 unlimited), `IsActive`, `CurrentState`.
  `SetupAbilityContext` gives the static record: `RecordKey`, `TargetType` (with colour
  markup such as `[[col:green]]Self[[/col]]`), `ManaUsed`, `RechargeTime` (the Herald:
  Foe Seeker 60 s; Tormentor Sword, Deadly Onslaught and Locus of Wrath 90 s; Banner of
  Hellfire 120 s).
- `CcoBattleRoot` with id `""` reaches the player's army: `PlayerArmyContext`.
  `ArmyAbilitiesList(false)` lists the army abilities in cost order. Khorne's:
  - `horn_of_khorne`, target Ground or Ally, radius 35 m, recharge 90 s, active 31 s;
  - `relentless_rage`, target Ally, recharge 90 s, active 20 s;
  - `blade_of_khorne`, target Ground, recharge 120 s, active 8 s.

  `ArmyAbilityCurrency` counts the points (0 at the start, 113 by 514 s in a 531 s
  battle). `ArmyAbilityIndexCost(i)` is 100, 200 and 300, and `IsArmyAbilityUnlocked(i)`
  turned true for index 0 at 100 points. `HasArmyAbilityFillCurrency` is true.
  `ArmyAbilityIndex(key)` returned nil; `ArmyWideEffects` was empty.
- The HUD shows them at `army_ability_container > army_ability_parent >
  button_holder_<key> > button_ability_<key>`. The button state is `inactive` while
  locked and `active` once unlocked; children `lock`, `dy_time_remaining` (cooldown
  text) and `cooldown_blocked`. The `lock` icon is hidden on unlocked abilities and also
  on the one being charged, so it does not mean unlocked. The button's
  `CcoBattleAbility` id (`<key>_<pointer>`) did not resolve through `get_context_value`.
- Casting: `bm:get_player_army():use_special_ability(key, battle_vector, 0, 0)` at the
  largest unit's position was accepted (Horn of Khorne, unlocked at 109 points, at 260.5 s
  in `probe-abilities-random-s245-20261014`). The button then read `selected_inactive`
  with `dy_time_remaining` counting the 31 s active phase, then `inactive` counting the
  90 s recharge. Unit abilities cast the same way showed `IsActive` true and
  `CanCurrentlyPerform` false afterwards, and a potion 0 uses left
  (`probe-abilities-random-s4-20261013`).
- Inside a list expression (`JoinString`, `Filter`) the root's `PlayerArmyContext` and
  `PlayerAllianceContext` do not resolve (they come back empty), but the globals
  `PlayerArmy` and `PlayerAlliance` do; literal ids work too.
- Unit names: `UnitRecordContext.Name` and `UnitDetailsContext.Name` both returned
  "Herald of Khorne"; `OnscreenName` and `LocalisedName` returned nil. Names are
  presentation data only.

## Battle types (probed 2026-10-14)

Evidence: `probe-battle-types-20261014/` (all ten lobby types), `battle/smoke-*` and
`probe-conquest-attack-20261014`. Scenario/mode definitions stay in
[battle-types.md](battle-types.md), maps in `custom_battle.json`, observation fields in
`engine/mailbox.py`. The engine quirks worth preserving:

- Mode selection changes the lobby shape. Survival removes AI slots and forbids adding
  them; switching away does not restore them. Free-for-all slots also persist. Survival
  and domination hide the timer and refuse Start without reserves. Attacker/defender roles
  do not apply to survival, domination or free-for-all; ordinary battle types read the
  player's role through `LocalPlayerSlotContext.TeamContext.IsAttacker`.
- `BattleTypeState` identifies the native battle mode. Alliance indices are zero-based in
  UI contexts and one-based in battle Lua. Free-for-all has four alliances;
  `bm:get_non_player_alliance()` returns only one of the opponents.
- Objective help text includes both game rules and HUD descriptions; `mode` keeps the
  former. Capture-point keys can repeat (four `capture_point_tower_only` in Helmgart),
  and `Radius` read zero. Alpine Ridge has one point, Arnheim three: a mode name alone
  does not establish a distributed-control task.
- Tickets count up towards 600/1500 in the conquest/domination examples, but siege
  defenders begin with 1000 and lose them with capture points. Survival's goal read -1.
  The `TimeoutWinningAllianceIndex` is the defender, or -1 in free-for-all.
- Supplies accrue while a policy thinks. Siege began with 6000 and gained about 9/s;
  survival 1000 and about 20–25/s; domination 500, plus its stated damage income. Do not
  compare exact supplies without matching elapsed time.
- Build slots include disabled/unbuilt building options. `CanAfford` returned false even
  when affordable; evaluating a buildable's `PrimaryAction` through `get_context_value`
  built it and spent supplies. Eight piercing towers were built at 5.5 s for 500 each;
  construction took 75 s. This unusual query-with-effects belongs only in order dispatch.
- `BattleReinforcementPoolContext.UnitsForArmy(PlayerArmyContext, 1)` returned the pool;
  argument zero returned empty. `PurchaseUnit` requires `call_context_command` (the same
  expression through `get_context_value` did nothing). Available zones can still refuse
  a particular purchase, and one unit type can have multiple costs.
- Purchased units join the army's live `units()` as they enter. Destroyed/rebought units
  can return with the same `unique_ui_id`: 21 purchases added only six ids in one trial.
  The reinforcement-army list also contains unbought pools, whose units are not valid
  targets. A separate one-second scan registers purchases/waves; tying scans to forced
  observations previously starved them.
- Amaxon Plain's crossings were terrain, with no buildings or capture points. Backwoods
  Path's objective mentioned an escape zone, but `HasAmbushWithdrawArea` was false and
  its position (0,0). The Hunting Fields began with ten enemies, eleven queued enemy
  armies and three victory locations; its barriers open as waves finish.

## Advisor text (probed 2026-10-13)

`common.advice(text)` from the battle script opens the advisor (`advice_interface` turns
visible) and shows the text as is, in a custom battle unpaused at 1x; each call replaces
the previous text. `play --show` sends each model reply as `say` with the orders; in
`commander-luna-v2-rand-2028855463` the advisor's `Text` component read "23 s: gpt-6-luna
plan from the state at 15 s / Keep the infantry advancing together, ... / f8 shoot e3".
The debug `bm:queue_advisor` is not needed.

## Visual recording and presentation (probed 2026-10-15)

- The 1 Hz replay recorder cost 2.851 ms CPU per sample in its scripted off/on pair, with
  battle/wall clock ratios 0.998213 off and 0.997703 on; one pair does not establish an
  exact overhead.
- `common.take_screenshot` writes the requested TGA (1920×1080, 8,294,418 bytes) but took
  43.007 ms inside the battle script. `--stills` instead uses Pillow `ImageGrab` in a
  separate Windows Python process (`engine/windows_capture.py`), which checks the game
  PID owns the foreground window and the job and battle identity before and after each
  capture; a failure becomes metadata, never an order error. Capture times are bounded
  by the surrounding observation timestamps, not an exact render time.
- The ordinary battle camera clamps altitude and pitch; `change_height_range(5,800)` did
  not lift the limit. `bm.battle:enable_cinematic_camera(true)` followed by
  `camera:move_to` reached a requested 500 m overhead position and target exactly. The
  flag changes the camera only: no cutscene, pause, slowdown or desktop input.
- Stills are not registered to map coordinates; reports show them beside the public
  grid.

## Declared mode and reinforcement checks (2026-10-16)

`SettingsContext.BattleTypeRecordContext.Key` identifies the selected lobby mode.
`MapContext.BattleTypeString` is generic `land_normal` even for the Hunting Fields
survival map and Helmgart siege, so it is not a mode check. The first battle observation
separately verifies the engine's type. Survival's `IsTimeLimitUsed` is false although
`TimeLimitSeconds` retains the last hidden lobby setting; the battle must report -1.

`PlayerSlotList.At(n).SetIsRecruitingReinforcements(true)` selects the reserve pool for
ordinary card recruitment. `ClearReinforcements()` clears it, and switching false returns
to the starting army. `ReinforcingUnitList.JoinString(UnitRecordContext.Key, ";")` reads
it back. The lobby sorts by unit class; compare multiplicities. These commands recruited
the fixed seven-unit Kislev pool in the b12 lobby probe. Main army and pool checks still
run against the first battle observation before any policy decision.

## Unverified

From the documentation or code reading; probe before relying on them:
- `is_hidden()` for enemies in cover. The mod shows an enemy only while
  `is_visible_to_alliance` holds and `is_hidden` does not.
- `os.rename` collisions while the controller reads a file.
- A restart requested before the battle is decided: the script calls `RestartBattle`
  after 3 s without a results popup. `play` never sends one.
- `ToggleFlying` during its transition animation or under combat restrictions.
- Same-tick combat and timer expiry (see [Result, timer and restart](#result-timer-and-restart)).
- Lobby-setting persistence after a graceful menu exit, and what a later undeclared job
  inherits; disturbed difficulty/scale/realism did not survive the tested supervised shutdown.
- Experience and saved presets outside the live verification scenario (including
  reinforcement ranks); policy strength and difficulty calibration from XP are unverified.

## Finding another capability

Start with the installed build's own references, not a broad web/API inventory:

1. Read the relevant battle API HTML or one named context's section in
   `documentation/ui/documentation.html`. The latter is a single large line: parse the
   HTML and print only the selected heading/table, rather than sending a raw `rg` hit to
   an agent. The community mirror below is convenient but may describe an older build.
2. Inspect the actual UI binding when signatures are absent. In `data/ui3.pack`,
   `ui\frontend ui\custom_battle.twui.xml` binds race/faction/recruitment;
   `custom_battle_map_settings.twui.xml` binds settings; `custom_battle_unit_upgrades.twui.xml`
   binds mounts, variants and equipment. Search a named `context_function_id` and its
   argument expressions, not the whole XML. `engine.pack.extract` can read an entry in
   memory; `pack --extract PACK NAME` can save a focused reference under ignored `runs/`.
3. State the desired observable result and its independent reference before probing.
   Use the current job's `menu` request, check its exit status, and save the relevant
   readbacks/source/build. A query that returned a value is evidence of that query, not
   proof of a completed order or a useful policy feature. Agree a repeatable check
   before calling the behavior verified.

Useful candidates, **documented but not live-checked in this review**:

| Capability | Concrete use and check before adoption |
|---|---|
| `unit:unit_distance`, `unit_in_range` | Bounding-box separation and engine missile range could clarify withdrawal/range decisions. Compare approach, overlap, melee and withdrawal with rendered formation boundaries; zero separation alone must not mean contact. |
| Flank-threat methods; `is_controllable` / `IsOrderable` | Diagnose pin-then-rear or refusals. Compare controlled front/side/rear approaches and rout/rally with HUD and order response; filter threat identities by current visibility. |
| `CcoCustomBattleUnit.ChangeUnitType`, upgrade `ToggleEquipped` | Fix a caster's lore/spell/equipment loadout. Compare declaration, lobby, saved-preset reload and battle-owned abilities, including duplicate casters with different loadouts. |
| `CcoBattleResultUnit.DamageDealt`, `DamageDealtCost`, `NumKillsFriendlies` | Private post-battle diagnosis of spells/artillery. Compare the rendered results statistics, zero-shot units and rematch resets before changing any scoring. |
| Settings for time of day, weather and season | Potential scenario conditions. Add fields only for a planned experiment, with declared/read-back/restarted checks. |

## References

The CA scripting documentation, mirrored by the community (some pages carry a 2024
date); the extracted copy in `runs/twwarhammer3/vanilla/` is authoritative for this
patch:
- [battle scripting index](https://chadvandy.github.io/tw_modding_resources/WH3/battle/battle_index.html)
  and [scripting overview and logging](https://chadvandy.github.io/tw_modding_resources/WH3/index.html)
- [core: mod loading](https://chadvandy.github.io/tw_modding_resources/WH3/battle/core.html#function:core:load_mods),
  [battle_manager](https://chadvandy.github.io/tw_modding_resources/WH3/battle/battle_manager.html),
  [battle](https://chadvandy.github.io/tw_modding_resources/WH3/battle/battle.html),
  [timer_manager](https://chadvandy.github.io/tw_modding_resources/WH3/battle/timer_manager.html)
- [battle_unit](https://chadvandy.github.io/tw_modding_resources/WH3/battle/battle_unit.html),
  [battle_unitcontroller](https://chadvandy.github.io/tw_modding_resources/WH3/battle/battle_unitcontroller.html),
  [battle_army](https://chadvandy.github.io/tw_modding_resources/WH3/battle/battle_army.html),
  [battle_units](https://chadvandy.github.io/tw_modding_resources/WH3/battle/battle_units.html),
  [battle_vector](https://chadvandy.github.io/tw_modding_resources/WH3/battle/battle_vector.html)
- [Lua 5.1 reference manual](https://www.lua.org/manual/5.1/manual.html)
