# WH3 integration facts

Verified against the installed game unless marked otherwise. Patch 9.0.3, build 4366297
(2026-10-07), Steam buildid 25823491, `Warhammer3.exe` sha256
`518c4f292f275142df13b96b9db704a3db7b4870b2c519df83d850596ecc822a` (pinned in
`engine/runtime.py`). Windows Python 3.13.1 at `C:/Python313/python.exe`. Preferences
at launch: fullscreen 1920x1080, unit size 2 ("large"), AI stats modifier 1.1, realism
off, multithreaded model on.

## Packs and loading

- Vanilla packs are PFH5. Header (28 bytes LE): `PFH5`, u32 type (1 release, 3 mod, 4
  movie), u32 dependency count, u32 dependency index bytes, u32 file count, u32 file
  index bytes, u32 timestamp; dependency names NUL-terminated; file index entries
  `u32 size, u8 compressed, backslash path, NUL`; data in index order. Patch 9 vanilla
  entries are compressed: u32 uncompressed size then a zstd frame (`engine/pack.py`
  reads them through the `zstd` CLI). The mod pack is written uncompressed with a zero
  timestamp, so its hash depends only on the sources.
- Launch route that worked: `Warhammer3.exe twwarhammer3_mods.txt;` from the game folder,
  the list holding `add_working_directory "C:/wh3-agent/mods";` and
  `mod "twwarhammer3.pack";`. The main menu shows "(modded)". A direct launch works with
  Steam running (`steam_appid.txt` is in the game folder).
- `script/_lib/lib_header.lua` creates `core`, `bm` (battle), `tm` (frontend) and then
  requires `lib_mod_loader.lua`, which calls `core:load_mods("/script/_lib/mod/",
  "/script/battle/mod/")` in battle and `"/script/frontend/mod/"` in the frontend; each
  `*.lua` runs at top level under `pcall` (no `execute_mods` outside campaign). Every load
  is written to `<game>/lua_mod_log.txt` ("Mod [...] loaded successfully" or the error).
- Lua 5.1 in the frontend has `io.open` on absolute Windows paths, `os.remove`,
  `os.rename`; `tm:repeat_real_callback(fn, ms, name)` works in the frontend. (Battle
  equivalents are documented, not yet exercised.)

## Frontend automation

- `find_uicomponent(core:get_ui_root(), name1, name2, ...)`, `uic:SimulateLClick()`,
  `uic:Id()`, `uic:Visible()`, `uic:ChildCount()`, `uic:Find(i)` (0-based) and
  `uic:CurrentState()` all work from a frontend mod; the tree dump of the main menu is
  `runs/twwarhammer3/launch-m1/ui_tree.txt` and of the custom battle screen in
  `roster.txt`, `teams.txt`, `army.txt`, `header.txt` beside it.
- Main menu: `buttons_holder/button_battle`, then `battle_frame/button_practice_battle`
  opens "Skirmish vs A.I." (the custom battle). Both clicks worked by simulation.
- Custom battle screen (`custom_battle`): tabs `button_tab_armies`/`button_tab_maps`;
  teams `CcoCustomBattlePlayerSlotslot0` (player) and `...slot1` (CPU) under
  `teams_parent`, `button_add_ai`, `button_swap_attacker_defender`; army header buttons
  `button_load_preset`, `button_save_preset`, `button_clear`, `button_autogen`; map
  settings `map_listview/list_box`, `checkbox_large_armies`, `dropdown_funds_type`;
  `start_button_frame/button_start_battle` (inactive until both armies have units).
  Unit cards: `recruitment_options_list/CcoUiUnitGroupParentRecord<group>/unit_list/
  CcoUnitsCustomBattlePermissionRecord<unit key>:<faction key>:<n>/unit_card`; groups
  seen: commander, heroes_agents, infantry, cavalry_chariots, missile_cavalry_chariots,
  monster_beasts, artillery_war_machines. The screen remembered the last factions (Khorne
  vs Dwarfs, map "An Ogre's Folly") across launches but not the armies.
- A simulated left click on `unit_card` pins the unit's info panel; `SimulateDblLClick()`
  on the same `unit_card` recruits the unit (verified 2026-10-13 for both slots: select the
  slot, `button_bar_parent/button_clear`, then double-click each card). The sequence is
  `configs/twwarhammer3/menu.json`. The screen keeps the last factions across launches, so
  the steps assume Khorne (player) against Dwarfs.
- Intro movies: the frontend script loads about 25 s after launch, but its real-time
  callbacks do not run until the intro movies end on their own, about 2 minutes later.
  No key press is needed; the first menu step waits for `buttons_holder/button_battle`.
- The frontend script unloads with the battle loading screen, so a step sequence that
  starts a battle never reaches its end; the controller takes the battle's first
  observation as the end of the menu.

## Battle

Verified 2026-10-13 in `runs/twwarhammer3/battle/attack-m3-20261013` (Khorne vs Dwarfs,
5 units each, map "An Ogre's Folly").

- The mod loader runs the battle script once per battle load, after `bm` exists.
  `bm.battle:end_current_battle_phase()` ends deployment (logged "ok" about 4.7 s into
  the battle), and the `Deployed` phase callback fires right after.
- One `unitcontroller` per friendly unit (`army:create_unit_controller()`, `add_units`,
  `take_control`) applies `goto_location`, `attack_unit(target, true, run)` and `halt`.
  The engine drops an attack when the target dies or leaves sight: the unit shows no
  `current_target`, `is_idle()` is true, and it stands still until ordered again.
  `ordered_position()` is the unit's own position while it attacks (per the docs).
- Unit fields that read correctly: `position()`, `bearing()`, `number_of_men_alive()`,
  `initial_number_of_men()`, `unary_hitpoints()`, `ammo_left()`, `starting_ammo()`,
  `missile_range()`, `slow_speed()`/`fast_speed()`, `fatigue_state()` (e.g.
  `threshold_winded`), the state flags, `current_target()` (mapped through
  `unique_ui_id()`), `is_visible_to_alliance(alliance)`. `is_cavalry()` and
  `is_artillery()` were false for Marauder Horsemen and the Skullcannon; the class now
  comes from `unit_class()` (land_units class, e.g. `art_fld`).
- Axes: bearings agree with x east and z north and 0 = +z, clockwise (a unit at
  (-174, 34) facing 213 was attacking an enemy at (-192, 13), bearing 221 from it).
- The result: at `VictoryCountdown`, `battle_outcome_decided()`, `victorious_alliance()`
  and `local_alliance()` gave "lost" when the player's army broke.
- Restart: `bm:restart_battle()` (the `RestartBattle` context command on `CcoBattleRoot`)
  did nothing on the results screen. `bm:end_battle()` ends the victory countdown, the
  results popup's `in_battle_results_popup/.../button_rematch` asks "Are you sure you
  want to rematch this battle?", and `dialogue_box/both_group/button_tick` confirms; the
  same battle reloads in about 15 s with a fresh script environment.
- The battle script can run the same UI steps as the frontend (`ui` control,
  `menu --battle`): the battle UI root holds `menu_bar`, `panel_manager`, `dialogue_box`.
- The game ships its scripting documentation as HTML in `data.pack`
  (`documentation/script/battle/*.html`) and its script libraries in `data_script.pack`
  (`script/_lib/lib_battle_manager.lua`, ...). Extract them with `pack --extract` into an
  ignored folder (`runs/twwarhammer3/vanilla/`); they are proprietary.

## Unverified (from the documentation; probe before relying on them)

`bm:repeat_callback`/`repeat_real_callback` behaviour under `modify_battle_speed(0)`
(pause mode); `goto_location_angle_width` facing and width; `is_hidden()` for enemies in
cover; `os.rename` collisions while the controller reads; a restart requested before the
battle is decided (the script calls `RestartBattle` after 3 s without a results popup).
