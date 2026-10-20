# WH3 integration facts

How the installed game behaves, verified in the engine unless a line says otherwise or it
sits under [Unverified](#unverified). Evidence paths are under `runs/twwarhammer3/`; a
`bN` or `vN` label names the [log.md](log.md) entry that holds the run. The interface
itself is documented in the code: the `engine/mailbox.py` docstring (bridge files and
observation fields), `protocol.py` (orders), the `battle/setup.py` docstring (scenario
fields) and `ui.run` in `mod/script/_lib/mod/twwarhammer3_ui.lua` (menu step types).

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
- Lua 5.1 environment: `io.open` on absolute Windows paths, `os.remove` and `os.rename`
  work in both scripts, as do `tm:repeat_real_callback(fn, ms, name)` in the frontend and
  `bm:repeat_real_callback` in battle. There is no `math.huge`. `loadstring` chunks run in
  the global environment, without `bm`; the `lua` menu step gives them the mod's
  environment with `setfenv`.
- The game ships its scripting documentation as HTML in `data.pack`
  (`documentation/script/battle/*.html`, `documentation/ui/documentation.html`) and its
  script libraries in `data_script.pack` (`script/_lib/lib_battle_manager.lua`, ...).
  `pack --extract PACK NAME > runs/twwarhammer3/vanilla/NAME` copies one entry into the
  ignored folder; they are proprietary and are the authoritative local reference.

## Frontend automation

- `find_uicomponent(core:get_ui_root(), name1, name2, ...)`, `uic:SimulateLClick()`,
  `uic:Id()`, `uic:Visible()`, `uic:ChildCount()`, `uic:Find(i)` (0-based) and
  `uic:CurrentState()` work from a frontend mod. Tree dumps of the main menu and the
  custom battle screen are in `runs/twwarhammer3/launch-m1/`.
- Main menu: `buttons_holder/button_battle`, then `battle_frame/button_practice_battle`
  opens "Skirmish vs A.I." (the custom battle). The first menu step waits up to 240 s for
  the first button; no key is pressed.
- Custom battle screen (`custom_battle`): tabs `button_tab_armies`/`button_tab_maps`;
  teams `CcoCustomBattlePlayerSlotslot0` (player) and `...slot1` (CPU) under
  `teams_parent`, `button_add_ai`, `button_swap_attacker_defender`; army header buttons
  `button_load_preset`, `button_save_preset`, `button_clear`, `button_autogen`; map
  settings `map_listview/list_box`, `checkbox_large_armies`, `dropdown_funds_type`;
  `start_button_frame/button_start_battle` (inactive until both armies have units).
- Unit cards: `recruitment_options_list/CcoUiUnitGroupParentRecord<group>/unit_list/
  CcoUnitsCustomBattlePermissionRecord<unit key>:<faction key>:<n>/unit_card`; groups
  seen: commander, heroes_agents, infantry, cavalry_chariots, missile_cavalry_chariots,
  monster_beasts, artillery_war_machines. The last field is 1 for lords and 0 for other
  units. A caster with several lores has one card: the lobby offers
  `wh2_main_skv_cha_grey_seer_plague_0`, not `_ruin_0` (the first swarm screen stopped on
  it, 2026-10-15). Setup dumps each army's cards to `cards_slot<N>.txt` in the job before
  recruiting. A simulated left click pins the unit's info panel; `SimulateDblLClick()`
  recruits it into the selected slot (select the slot, `button_bar_parent/button_clear`,
  then double-click each card). Cards are found without waiting for them to read as
  visible; legendary lords use the race's main faction key
  (`wh_dlc01_chs_cha_prince_sigvald_the_magnificent:wh3_main_sla_slaanesh:1`).
  A listed card does not prove the unit is available: the Warplock Jezzails card
  (`wh2_dlc12_...`, The Prophet & the Warlock, presumably not owned) was found and
  double-clicked without recruiting; setup's unit-count check stopped the job (2026-10-16).
- Race: `faction_pic_mask_parent/button_select_race` opens a popup of
  `CcoSubcultureRecord<subculture>` entries (25, e.g. `wh_main_sc_emp_empire`); clicking
  one switches the selected slot's race and unit cards. The popup never reads as visible
  from the root, so the click step cannot wait for it.
- Faction: `faction_pic_mask_parent/dropdown_context_scroll` lists the race's
  `CcoFactionRecord<faction>` entries; clicking one selects it, and both slots accept the
  same faction. Without that step the game picks a faction, which varied between jobs.
  A faction appears cosmetic (the owner's observation): it carries the banner colours,
  unit card ids keep the race's main faction key, and Autogenerate fills the army from
  the race, so random draws pick only the race. Beastmen and Undead Legions show no
  factions (DLC not owned, presumably); `configs/twwarhammer3/custom_battle.json` lists
  the other 23 races (307 factions) and the maps per battle type.
- Autogenerate: `button_bar_parent/button_list/clear_autogen_parent/button_autogen` beside
  `button_clear` fills a cleared army (11 Khorne units at the "large" funds setting). The
  UI texts say it is disabled while Unit Caps is on; `checkbox_unit_caps` is off on this
  profile.
- Maps tab: battle types `map_type_list/CcoBattleTypeRecord<type>` and, per type,
  `map_listview/.../CcoCustomBattleMap<preset key>` entries (380 for classic).
  `button_random_map` picks one. A map chosen without starting a battle did not persist.
- The lobby keeps the last races and map across launches (not the armies), and the last
  battle type and AI slots between battles; `setup.scenario_steps` therefore sets them
  every time.
- The frontend script unloads with the battle loading screen, so a step list that starts
  a battle never reaches its end; the controller takes the battle's first observation as
  the end of the menu.

### Lobby settings and declared scenarios

- Settings dropdowns are `dropdown_<name>/popup_menu/list_box/
  CcoCustomBattleSettingRecord<option>`: `dropdown_funds_type` (`funds_large`,
  `funds_custom`), `dropdown_unit_scale` (`unit_scale_small`, `_normal`, `_large`,
  `_ultra`), `dropdown_time_limit` (`time_limit_short` 1200 s, `_medium` 2400 s, `_long`
  3600 s, `_unlimited`), `dropdown_difficulty` (`ai_level_sandbox`, `_easy`, `_normal`,
  `_hard`, `_very_hard`); the AI stat modifier is a slider (`ai_stat_mod_slider`). This
  profile had large funds, large units, the long timer and very hard AI; realism, large
  armies, unit caps and multiple lords off; "allow no lord" on.
- A scenario with `expect` sets its settings through context commands on
  `CcoFrontendRoot` (`setup.menu_checks`), under `CustomBattleLobbyContext.SettingsContext.`:
  `SetTimeLimitSettingContext(TimeLimitSettingList.FirstContext(Key == "<timer>"))`,
  `SetBattleAiStatsModifier(<value>)`,
  `SetFundTypeSettingContext(FundTypeSettingList.FirstContext(Key == "<funds>"))` and,
  for custom funds, `SetCustomFundsAmount("<amount>")`. It then reads back
  `MapContext.BattleTypeString`, `DifficultyLevelSettingContext.Key`,
  `FundTypeSettingContext.Key`, `TimeLimitSeconds`, `BattleAiStatsModifier` and
  `CustomBudgetAmount`. Difficulty is checked, not set. Set and read back in the engine:
  the short 1200 s timer and modifiers 1.0 and 1.1 (b2).
- The lobby refused the declared Herald rosters under the default funds; those scenarios
  declare custom funds of 30000.
- Mounts: `CustomBattleLobbyContext.PlayerSlotList.At(slot).UnitList.At(i).ChangeMount(
  ...AvailableMountsList.FirstContext(MountedUnitContext.Key == "<key>"))`, verified by
  reading `UnitRecordContext.Key` (`setup.scenario_steps`).
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
- Realism is a game preference the lobby cannot set; a declared scenario checks it
  against the profile before launch (`setup.check_preferences`).
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

First verified in `runs/twwarhammer3/battle/attack-m3-20261013` (Khorne against Dwarfs,
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
  script runs the same UI steps as the frontend from `menu.json` (`menu --battle`).

### Units and axes

- Unit fields that read correctly: `position()`, `bearing()`, `number_of_men_alive()`,
  `initial_number_of_men()`, `unary_hitpoints()`, `ammo_left()`, `starting_ammo()`,
  `missile_range()`, `slow_speed()`/`fast_speed()`, `fatigue_state()` (e.g.
  `threshold_winded`), the state flags, `current_target()` (mapped through
  `unique_ui_id()`), `is_visible_to_alliance(alliance)`.
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
move rejects its queued successors (verified with an unreachable first point). An
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
  the result time (verified on an isolated timer ending, b9). There is no end-cause
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
documentation is `documentation/ui/documentation.html` in `data.pack`. Verified on
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

Evidence: `runs/twwarhammer3/probe-battle-types-20261014/` (lobby dumps and read-backs of
all ten types, `probe_types.out`), the smoke jobs `runs/twwarhammer3/battle/smoke-*` and
`probe-conquest-attack-20261014`. The scenarios and the `mode` state they produce:
[battle-types.md](battle-types.md).

Lobby (custom battle screen):
- Battle type records `map_type_list/CcoBattleTypeRecord<key>`; maps per type: 380
  classic, 44 conquest, 21 domination, 13 free-for-all, 74 ambush, 69 river crossing
  (chokepoint), 20 underground intercept, 70 unfortified settlement, 38 siege, 29
  survival (`custom_battle.json` `battle_type_maps`).
- Read-backs on `CustomBattleLobbyContext.SettingsContext`: conquest, ambush, chokepoint,
  underground, settlements and sieges have attackers and defenders
  (`HasAttackerDefender`, `CanToggleAttackingTeam`); domination, free-for-all and
  survival do not. Conquest has a ticket limit (600 by default), domination 1500 and a
  reinforcing army; survival has a reinforcing army and no AI slot (`CanAddAi` false).
  Domination and survival hide the time limit. Siege adds a settlement level (level 1
  costs 0).
- The player's slot sits in the top team, the defenders (`AttackingTeamIndex` 1).
  `team_spacer/button_swap_attacker_defender` swaps the roles;
  `CustomBattleLobbyContext.LocalPlayerSlotContext.TeamContext.IsAttacker` reads them.
- Lobby expressions take `!`, `==` and `<` (`...PlayerSlotList.Size < 2`).
- Selecting survival removes the AI slot, and it stays removed after switching back to
  another type; free-for-all slots stay too. `bottom_team_parent/button_add_ai` adds an
  AI slot (it became `CcoCustomBattlePlayerSlotslot1`, then `slot2`, `slot3`);
  `CcoCustomBattlePlayerSlotslot<n>/button_remove` removes one.
- Domination and survival refuse to start without a reinforcing army: the start button
  stays inactive and `ReadyStatusText` reads "You must select some reinforcing units."
  `clear_autogen_reinforcement_parent/button_autogen_reinforcements` fills it (9 units in
  domination, 17 in survival).

Battle (context system on `CcoBattleRoot` unless noted):
- `BattleTypeState`: `conquest`, `domination`, `survival`, `settlement_standard` (siege),
  `settlement_unfortified` (minor settlement), `land_ambush`, `land_bridge` (chokepoint),
  `underground_intercept` and `land_normal` (classic, checked in b1, and free-for-all).
  `SetupContext.IsPlayerAttacker` gives the role and `TimeoutWinningAllianceIndex` the
  alliance that wins when time runs out (the defender; -1 in a free-for-all).
- Alliance ids in the context system are 0-based (the player's was 0) and the script's
  are 1-based. A free-for-all has four alliances (`bm:alliances():count()`);
  `bm:get_non_player_alliance()` returns only one of them.
- `BattleTypeCheatSheetList(0)` holds the objectives as the help panel words them, for
  example (conquest) "Destroy or rout all enemy units before the timer expires or reach
  500 victory tickets by seizing capture points." The column also explains the type's
  mechanics (capture points and tickets, supplies, reinforcements), which the state
  keeps, and the interface (time limit, balance of power, unit buttons, abilities),
  which it drops.
- `CapturePointList`: `Key`, `DisplayName`, `Position.x/z`, `CurrentHolderAlliance` (-1
  for none), `IsContested`, `IsLocked`, `CapturePercent` (0-1), `ContributesToVictory`.
  `Radius` read 0. Keys repeat: a siege had four `capture_point_tower_only`.
  Alpine Ridge Conquest has one central point; Arnheim Domination has three separated
  points. A mode name alone does not establish a distributed-control challenge.
- Tickets: `AllianceList.TicketsRemaining` counts up in conquest and domination (+1/s
  for holding one point, +2/s for two) towards `CaptureLocationManagerContext
  .TicketsGoal` (600, 1500). A siege defender starts with 1000 (`StartingTickets`, goal
  0) and loses them with its points (`CapturePointScore` -500 for the key building).
  Survival's goal reads -1.
- Siege (Helmgart): 100 buildings, 36 enabled (key building, about 30 wall pieces,
  gatehouse, four fort towers). `BuildingsList.Filter(IsGate)` gives the gate's
  `GateCurrentHitpoints`/`GateMaxHitpoints`. Unbuilt tower options are buildings too
  (`IsEnabled` false). The AI attacker had no siege equipment (`VehicleList` empty).
- Supplies: `PlayerArmyContext.GlobalCurrency` when `HasSupplies`. The siege defender
  starts with 6000 and gains about 9/s (6495 at 60 s, 9890 at 508 s with nothing built);
  survival starts at 1000 and gains about 20-25/s (1120 at 12 s, 1853 at 46 s, 3392 at
  100 s); domination 500, plus "additional supplies by dealing damage".
- Building slots, `ToggleableSlotList(PlayerArmyContext)`: siege 8 tower slots (four
  options, 500-2000), minor settlement 22 slots: 11 barricade slots (four options,
  300-500) and 11 tower slots (the siege's four options).
  `IconPathForIndex(army, Index)` names the options (`tower_piercing_1`,
  `tower_cannon_4`, `barricade_trap`, ...); `Cost(0)` gives the cost; `CurrentIndex` the
  built option; `IsConstructionInProgress` and `ConstructionTimeRemainingSeconds` the
  construction (75 s for a piercing tower). `CanAfford(...)` read false even when
  affordable. Evaluating `...BuildablesList.FirstContext(Index == i).PrimaryAction` with
  `common.get_context_value` built the tower: supplies dropped by its cost. The siege
  army built a `tower_piercing_1` on all 8 slots at 5.5 s (500 each).
- Reinforcement pool: `BattleReinforcementPoolContext.UnitsForArmy(PlayerArmyContext, 1)`
  lists it (with 0 the list was empty), `CostPerUnit(army id)` the costs.
  `SpawnZoneList` with `IsAvailableToAlliance(id)` gives the army's zones (ids 6-10 in
  domination). `common.call_context_command("CcoBattleRoot", "", "BattleReinforcement
  PoolContext.PurchaseUnit(<pool>.At(1), PlayerArmyContext, 6)")` bought a unit: supplies
  fell by its cost and it walked in from zone 6. The same purchase through
  `get_context_value` did nothing. `CanPurchaseUnit(unit, army, zone)` changes during the
  battle and depends on the unit: zones open to the alliance refused at times, and a
  unit bought back while recovering was refused everywhere. One type can sit in the pool
  at two costs (survival marauders 446 and 400).
- A bought unit joins its army's `units()` list as it enters. A destroyed unit goes back
  to the pool and, bought again, returns as the same unit (`unique_ui_id`), keeping its
  id in the state (21 purchases in the llm domination battle gave 6 new ids). The
  reinforcement armies (`bm.battle:reinforcements():reinforcement_army(i):army():units()`)
  hold the unbought pools, ours and the enemy's, every unit `is_valid_target()` false.
  The mod scans both on its own one-second timer (scanning with each observation
  starved when a policy forced an observation with every acknowledgement); bought units
  and survival waves register about a second after they arrive.
- Chokepoint (Amaxon Plain): no buildings (`BuildingsList.Size` 0) and no capture
  points.
- Ambush (Backwoods Path): the objective text names an escape zone for the defender,
  but `HasAmbushWithdrawArea` is false in this custom battle and
  `AmbushWithdrawAreaPosition` reads (0, 0).
- Survival (The Hunting Fields): 10 enemy units at the start and eleven enemy
  reinforcement armies queued (ten of 20 units, one of 2), three victory locations, no
  building slots at the start. "Objective: Each wave will open the barrier to the next
  area of the map."

## Advisor text (verified 2026-10-13)

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
- Whether the lobby settings a declared scenario set (timer, AI stats modifier, funds)
  persist into a later undeclared job, which leaves them as the lobby has them.
- Experience and saved presets outside the live verification scenario (including
  reinforcement ranks); policy strength and difficulty calibration from XP are unverified.

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
