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
- A simulated left click on `unit_card` pins the unit's info panel; the army stays empty.
  Recruiting therefore needs another event (double click, a context command, or the
  autogen button): unverified.
- The desktop helper's screenshot (PowerShell `CopyFromScreen`) captures the fullscreen
  game. Real input through `SendInput` goes to whatever window is in front, which was
  the owner's terminal during the one test; not used for control.

## Unverified (from the documentation; probe before relying on them)

`bm:repeat_callback`/`repeat_real_callback` behaviour under `modify_battle_speed(0)`;
`bm:restart_battle()` during VictoryCountdown; `battle:end_current_battle_phase()` or
`button_battle_start` to end deployment; `victorious_alliance()`/`local_alliance()`
values; `is_visible_to_alliance`; axis signs (x east-west, z north-south per the
docs) and the bearing convention; `os.rename` collisions while the controller reads.
