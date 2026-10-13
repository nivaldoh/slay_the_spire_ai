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
- Startup skip: `engine/startup.py` installs a separate type-4 PFH5 movie pack,
  `data/zzz_twwarhammer3_skip_intro.pack`, with 18 entries (five startup movies and 13
  localized epilepsy warnings). Movie packs load without a mod-list entry. The 595-byte
  blank CA-VP8 is from MIT-licensed
  [twpatcher](https://github.com/Frodo45127/twpatcher/blob/a5783c5803d08cc4d5cdc40c9411549a55001c60/src/games/mod.rs);
  its license and source hash are beside the vendored clip in `src/twwarhammer3/assets/`.
  `gam_int.ca_vp8` is not overridden: `fe_game_intro_video_enabled false` disables its
  startup playback and preserves the cinematic viewer. Preparation checks that WH3 is
  stopped before writing any game files, preserves other preference bytes, and leaves
  matching packs/preferences untouched. The deployment record and read-only doctor
  expose the actual/expected pack hashes and effective preference.
  On 2026-10-13 the unmodified launch reached the menu in 149.014 s, versus 17.735 s
  after installing the skip (131.279 s saved in this single comparison). Both were
  supervised launches with the same project mod, measured when the visible Battle
  button was found; no key presses. Local evidence, screenshots, source fingerprints
  and preference snapshots: `runs/twwarhammer3/skip-intro-20261013/`.
  A direct executable launch with no arguments (Steam running, no project mod list)
  also reached the menu: visible in the capture completed at 20.774 s. Its Lua log
  contains no project scripts. The game's initial static loading splash remains.
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
  slot, `button_bar_parent/button_clear`, then double-click each card). The last field of
  a card id is 1 for lords and 0 for other units (`...general_0:wh_main_emp_empire:1`).
- Race: `faction_pic_mask_parent/button_select_race` opens a popup listing
  `CcoSubcultureRecord<subculture>` entries (25 on 2026-10-13, e.g.
  `wh_main_sc_emp_empire`); a simulated click on one switches the selected slot's race and
  its unit cards (verified 2026-10-13 for both slots). The popup never reads as visible
  from the root, so the step that clicks an entry cannot wait for it. The screen keeps the
  last races and map across launches; `play.scenario_steps` sets the races every time
  and leaves the map ("An Ogre's Folly") unless the scenario names one (random draws do).
- Faction: `faction_pic_mask_parent/dropdown_context_scroll` opens a list of the race's
  `CcoFactionRecord<faction>` entries (Khorne: khorne, arbaal, crimson_skull, ...); a
  click on one selects it for the selected slot (verified 2026-10-13), and both slots
  accepted the same faction. Without that step the game picked a faction itself, and it
  varied between jobs on both sides. Unit card ids keep the race's main faction key
  (`...:wh3_main_kho_khorne:1`) whatever faction is selected.
- Probe of 2026-10-13 (`runs/twwarhammer3/probe-random-army-20261013/`, dumps and steps):
  - Autogenerate army is `button_bar_parent/button_list/clear_autogen_parent/button_autogen`
    beside `button_clear`; a simulated click filled a cleared Khorne army with 11 units at
    the "large" funds setting. The UI texts say it is disabled while Unit Caps is on;
    `checkbox_unit_caps` is off (`<active>`) on this profile. The texts also name a
    `button_autogenerate`, which this screen does not have.
  - Maps tab: battle types `map_type_list/CcoBattleTypeRecord<type>` (`classic` selected;
    also conquest, domination, free_for_all, ambush, river_crossing_battle,
    underground_intercept, unfortified_settlement, siege, survival) and, for classic, 380
    `map_listview/.../CcoCustomBattleMap<preset key>` entries. `button_random_map` picks
    one and the list marks it `<selected>`. A map chosen without starting a battle did
    not persist: the next job began on the same map with the same start positions.
  - Settings on this profile, as `dropdown_<name>/popup_menu/list_box/
    CcoCustomBattleSettingRecord<option>`:
    - `dropdown_funds_type`: `funds_large` (the only other option, `funds_custom`,
      takes a typed amount);
    - `dropdown_unit_scale`: `unit_scale_large` (also `_small`, `_normal`, `_ultra`);
    - `dropdown_time_limit`: `time_limit_long` (also `_short`, `_medium`, `_unlimited`);
    - `dropdown_difficulty`: **`ai_level_very_hard`** (also `ai_level_sandbox`, `_easy`,
      `_normal`, `_hard`). Every battle so far ran at
    very hard. The AI stat modifier is a slider (`ai_stat_mod_slider`). Checkboxes:
    realism, large armies, unit caps and multiple lords off; "allow no lord" on.
  - The race list had 25 entries. Beastmen and Undead Legions showed no factions of
    their own (DLC not owned, presumably), so `configs/twwarhammer3/custom_battle.json`
    (23 races and the 380 classic maps) leaves them out. The owned races list 307
    factions in all.
  - A faction within a race appears to be cosmetic (the owner's observation): the faction
    dropdown carries the banner's primary and secondary colours, unit cards keep the
    race's main faction key whatever faction is selected, and Autogenerate fills the army
    from the race. Random draws therefore pick only the race.
- Before the startup skip, the frontend script loaded about 25 s after launch, but its
  real-time callbacks did not run until the intro movies ended, about 2 minutes later.
  The first menu step waits for `buttons_holder/button_battle`; no key press is sent.
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

- Historical pause mode (removed on 2026-10-13 at the owner's direction; verified
  earlier in `llm-luna-v4-pause-20261013`):
  `bm:modify_battle_speed(0, true)` stops model time, so the `repeat_callback` tick
  stops while `repeat_real_callback` polling continues; orders resume the battle and
  applied 600 ms of battle time after the state the model saw, whatever its think time.
  Current battles always run unpaused at 1x; the mod no longer pauses on publication
  or changes speed in response to orders. Old paused results remain labelled as such.
  Replacement engine smoke `skip-intro-20261013/play-smoke-realtime` verified five units
  per side, 77 acknowledged batches, zero invalid orders, and 23.4 battle seconds over
  23.401 wall seconds. All decision observations had `awaiting_orders=false`.
- `goto_location_angle_width(position, facing, width, run)` forms the unit up facing
  the given bearing (used by every v2+ battle line; the model's lines faced the enemy).
- `unit:can_reach_position(vector)` is false near the map edge: v2's withdrawals into
  the south-west corner (about x -500, z -480) had about 25 moves per episode rejected.

## Unverified (from the documentation; probe before relying on them)

`goto_location_angle_width` width; `is_hidden()` for enemies in
cover; `os.rename` collisions while the controller reads; a restart requested before the
battle is decided (the script calls `RestartBattle` after 3 s without a results popup).

Army abilities are not in the interface (owner report, 2026-10-13). These are army-wide
abilities that are not owned by a unit, such as the three Khorne abilities that unlock
as the army kills enemies. In a commander battle one became available near the end and
went unused. The mod reads only unit abilities (`owned_non_passive_special_abilities`),
so neither the state nor the order set includes them, for any controller. The
documentation offers:
- `battle_army:use_special_ability(key, position, [bearing], [width])`, with keys from
  the `army_special_abilities` table;
- battle currency through `army:has_currency(type)`, `army:currency_amount(type)` and
  `reset_currency_amount`, which presumably drives the Khorne unlocks.

It gives no getter for which army abilities an army owns or can use now. To probe:
- the battle UI's army ability panel (component ids and states), or the
  `army_special_abilities` table together with the currency amounts;
- a `use_special_ability` call on a Khorne army once one is unlocked.

## Expanded controller interface (2026-10-13)

Source starts at `863d10b`, with engine corrections in `50e3bee`, `0511302` and
`d76c5fa`. Evidence: `runs/twwarhammer3/capability-probes/`; these are diagnostic
battles with scripted interventions, not policy win-rate evaluations.

- `--interval-ms` defaults to zero. The observation acknowledging one request can be
  passed straight into the next decision. The live Luna smoke in `khorne-dwarfs-r3`
  issued seven decisions, six acknowledged before its time limit: every following
  decision used the acknowledgement's battle timestamp (0 ms extra gap), with no
  rejected orders. Think time averaged 9.399 s and wall roundtrip 9.744 s over the six
  acknowledgements. Cost $0.003063. The seventh request was outstanding at truncation.
  A positive interval still deliberately waits after issuing a batch.
- Friendly observations expose only supported behavior keys from `can_use_behaviour`,
  with `is_behaviour_active` values. Fire-at-will, skirmish and guard (`defend`) were
  toggled and read back in Khorne battles. `change_formation_spacing` and `formed_attack`
  were not supported by those units and are not offered for them.
- Move width 20 m was read back as 20; two queued waypoints reached the second point.
  `goto_location_angle_width_q` and `goto_location_q` are native engine queues.
  The formation center can stop several metres from the ordered point; a short-distance
  probe with a 5 m tolerance failed, while the longer path with a 15 m tolerance passed.
- An attack has `auto`, `ranged` or `melee` mode. Immediate attacks set `melee(bool)`;
  missile units' melee attacks select the secondary attack (`attack_unit`'s primary
  flag false), while units without missile range retain their primary melee attack.
  Queued attacks use `attack_unit_q` and its attack-method flag, so they do not toggle
  the mode before the preceding move finishes. In `khorne-dwarfs-r3`, the horsemen
  fired in ranged mode, then entered melee after a queued attack with 453 ammo left.
- Each acknowledgement has a one-based `index`, `unit`, `ok`, and `queued` flag.
  A failed move rejects its queued successors; an unreachable first point was verified.
  An acknowledgement reports a call issued to the engine, not visible execution. For
  native queues `applied_ms` is submission time, not the later start of each step.
  `command_queue` is labelled as the last submitted sequence; completion is unconfirmed.
- Active ability keys come from `owned_non_passive_special_abilities` and are checked
  again at dispatch. Calling `perform_special_ability(key)` without a unit argument
  raised `battle.unit expected, got no value` in the engine despite the optional target
  in the documentation. Self abilities pass the caster explicitly. Foe Seeker worked:
  the Herald's walk/run speeds rose from 1.9/4.8 to 2.4/6.0.
- `can_perform_special_ability` stayed true after Foe Seeker was cast. It is exposed as
  engine permission, not readiness; cooldown and uses remaining are explicitly unknown.
  Each ability reports its last issue time. The player's Winds of Magic pool and reserve
  are read from its army; individual spell costs are not currently supplied.
- `wizard-r3` (`6db8111`) used Balthasar Gelt (`wh_main_emp_cha_balthasar_gelt_0`)
  against the Empire mirror. Glittering Robe on friendly swordsmen reduced the magic
  pool 12 -> 7; Plague of Rust on visible enemy infantry 11 -> 7; ground-targeted
  Searing Doom 9 -> 3. Each order was acknowledged. A swordsman trying to use the
  wizard's ability was rejected as `unavailable_ability` by the Lua dispatcher.
  Separate casts when probing their effects: back-to-back spell requests in `wizard-r2`
  produced ambiguous pool changes (a later command can interrupt an earlier cast).
  Pool expenditure proves acceptance beyond the API call, not final damage or a
  completed effect on every target. Cooldown/damage attribution remains unmeasured.
