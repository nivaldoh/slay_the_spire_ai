# Total War: WARHAMMER III battles

Second game, started 2026-10-13. The question: can an API model (`gpt-6-luna`, low
effort, through `src/gameai/llm.py`) command a small army in a real-time custom battle
against the game AI, with the delay between the state it saw and the moment its orders
take effect measured and told to it, and can the autoresearch loop improve its
scaffolding? Campaign mode and model training come later.
[integration.md](integration.md) holds the verified engine facts; [guide.txt](guide.txt)
is the owner's modding guide that set the shape.

## How it works

Everything the game knows leaves it through a Lua mod, and every order enters the same
way. There is no external game API; the mod is the API.

- `src/twwarhammer3/mod/` is packed into `C:/wh3-agent/mods/twwarhammer3.pack` by
  `engine/pack.py` and loaded through a mod list the executable takes as its argument
  (`engine/runtime.py`). Three scripts: `script/_lib/mod/twwarhammer3_json.lua` (vendored
  rxi json.lua), `script/frontend/mod/twwarhammer3_frontend.lua` (drives the menus) and
  `script/battle/mod/twwarhammer3_battle.lua` (observations, orders, result).
- The controller in WSL talks to the scripts through files in `C:/wh3-agent/bridge/`
  (`engine/mailbox.py` documents the messages): `session.json` enables the scripts and
  sets speed, pause, intervals; `menu.json` carries frontend steps (find a UI component by
  id and click it, dump the UI tree, press a key, wait); `observation.json` is rewritten by
  the battle script every observation interval; `orders.json` holds one outstanding
  request (move, attack, halt per unit, or a `restart` control). The scripts are inert
  without a session file, so the installed pack changes nothing in ordinary play.
- Real-time by design: the battle keeps running while the model thinks. Every request
  carries the observation it was based on; the acknowledgement carries the battle time at
  which the orders applied, so `delay_ms` is measured per decision and goes into the next
  prompt. `--pause` is a labelled alternative (the script pauses after publishing and
  resumes when orders arrive; polling runs on UI time so it survives the pause).
- Policies see dicts (`protocol.py`): friendly units in full, enemy units only while
  `is_visible_to_alliance` says the player can see them, plus the enemy roster as the
  custom battle screen shows it. `battle/scripted.py` has `hold`, `attack_nearest` and
  `probe_move` (the axis probe). The LLM policy, the play loop, digest and the results
  register are not written yet; their design is in the session plan summarised below.

## Status (2026-10-13 01:00 local, paused by the owner)

| Milestone | State | Evidence |
|---|---|---|
| 1 Mod loads | done | `runs/twwarhammer3/launch-m1/lua_mod_log.txt` lists the json and frontend scripts loaded; `menu.log` has "frontend loaded" 25 s after launch |
| 1b Unattended custom battle | in progress | menu navigation by component id works (Battle, Custom Battle); UI tree dumps in `runs/twwarhammer3/launch-m1/*.txt`; a simulated single click on a unit card pins its info panel and does not recruit it |
| 2 Roster readable | not started | the battle script is written but has not run in a battle yet |
| 3–8 | not started | |

Open point for the owner: how to recruit units programmatically. `SimulateDblLClick`
support is in the frontend script (untested; the game must be relaunched to load the
rebuilt pack). If that also only pins the panel, the next route is the UI layout's own
context command for the card (the component ids are `CcoUnitsCustomBattlePermissionRecord
<unit key>:<faction>:<n>`, which are context objects), or `button_autogen` for a
generated army. Screenshots (`gameai/windows_desktop.py`) were only used to verify what a
click did; real mouse input is not part of the design and the one test of it hit the
owner's terminal window instead of the game.

## Commands

```bash
uv run python -m twwarhammer3 doctor                 # pins, preferences, running game, mod files
uv run python -m twwarhammer3 pack --list PACK       # entries of any pack; --extract PACK NAME
uv run python -m twwarhammer3 launch                 # build, install, run the game until Ctrl-C
uv run python -m twwarhammer3 menu --dump 4          # UI tree of the current screen (ui_tree.txt)
uv run python -m twwarhammer3 menu --steps steps.json  # click through components; tails menu.log
uv run python -m twwarhammer3 spend                  # runs/twwarhammer3/llm-spend.jsonl total
```

Nothing sends desktop input: the first menu step waits (up to 240 s) for the main menu
while the intro movies play out. An Escape press sent through `SendInput` once landed in
the Spire game and opened its settings screen, so the intro skip was removed.

## Planned next (from the approved session plan)

1. Recruit units by component (double-click or context command), select the CPU slot and
   recruit its army the same way, click `button_start_battle`; record the sequence in
   `configs/twwarhammer3/menu.json`. Then `play --episodes 2 --policy hold` must reach
   two results with nobody at the keyboard.
2. `battle/play.py`: job over episodes (restart through `bm:restart_battle()`), episode
   loop with the latency bookkeeping, `trace.jsonl` and `result.json`, exception mapping
   as in `spire.fullrun.play`; `--attach` to reuse a `launch`ed game.
3. `battle/llm.py` and `configs/twwarhammer3/system_prompt.md`: strict reply schema
   `{"orders": [...], "reason", "notes"}`, bounded notes and recent-orders memory, the
   timing line with the last measured delay, last-seen enemies.
4. Milestones 2–5 and 7 with facts into integration.md; then the first LLM battle,
   baselines, `docs/twwarhammer3/results.csv`, `stats`, and the autoresearch loop: three
   episodes of one fixed scenario per version, episode reviews in subagents, one change
   per version, `log.md` entries, a separate $25 ledger.
