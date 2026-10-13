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
  `probe_move` (the axis probe); `battle/llm.py` and `configs/twwarhammer3/` are the
  API-model policy and the autoresearch loop's editable surface.
- A job (`battle/play.py`) launches the game, runs the custom battle steps in
  `configs/twwarhammer3/menu.json` (no desktop input), plays episodes and restarts the
  same battle between them through the results popup's rematch button. Each episode
  writes `trace.jsonl` (every observation, prompt, reply and acknowledgement),
  `result.json` and `mod.log`; each finished episode appends a row to
  [results.csv](results.csv). Versions are logged in [log.md](log.md).

## Status (2026-10-13 06:45 local)

| Milestone | State | Evidence |
|---|---|---|
| 1 Mod loads | done | `runs/twwarhammer3/launch-m1/` |
| 1b Unattended custom battle | done | menu steps recruit both armies by double-click and start the battle; `runs/twwarhammer3/battle/*/menu.log` |
| 2 Roster readable | done | 5 v 5 units with positions, strength, fatigue, flags, targets in every observation |
| 3 Orders apply | done | attack, move (with facing) and halt through one unitcontroller per unit; acknowledgements carry the applied battle time |
| 4 Result | done | "lost" and "won" from the engine at VictoryCountdown, with both armies' true strength for evaluation |
| 5 Restart | done | rematch button and confirmation; three episodes per job |
| 6 Scripted baselines | done | `attack_nearest`: 3 wins of 3 at about 345 s |
| 7 First LLM battles | done | v1: 1 win of 3 |
| 8 Autoresearch loop | running | [log.md](log.md): v2 0/3, v3 3/5, v4 1/3 (1/3 paused), v5 4/6, v6 running |

Results by version: `python -m twwarhammer3 stats`. With outcomes this noisy (a version's
battles swing between a clear win and a clear loss), three episodes rank versions only
roughly; `own_left` and `enemy_left` (true strength at the end) add a finer measure.

## Commands

```bash
uv run python -m twwarhammer3 doctor                 # pins, preferences, running game, mod files
uv run python -m twwarhammer3 pack --list PACK       # entries of any pack; --extract PACK NAME
uv run python -m twwarhammer3 launch                 # build, install, run the game until Ctrl-C
uv run python -m twwarhammer3 menu --dump 4          # UI tree of the current screen (ui_tree.txt)
uv run python -m twwarhammer3 menu --steps steps.json  # click through components; tails menu.log
uv run python -m twwarhammer3 menu --battle --steps steps.json  # the same in a battle (mod.log)
uv run python -m twwarhammer3 play --policy llm --budget-usd 25 --scenario kho5-dwf5 \
    --episodes 3 --output runs/twwarhammer3/battle/llm-luna-vN-YYYYMMDD
uv run python -m twwarhammer3 digest runs/twwarhammer3/battle/<job>[/episode-0000]
uv run python -m twwarhammer3 stats                  # results.csv by policy, harness and mode
uv run python -m twwarhammer3 spend                  # runs/twwarhammer3/llm-spend.jsonl total
```

Nothing sends desktop input: the first menu step waits (up to 240 s) for the main menu
while the intro movies play out. An Escape press sent through `SendInput` once landed in
the Spire game and opened its settings screen, so the intro skip was removed.

## The loop

As for Spire full runs: play three episodes of the fixed scenario per version (`play`
needs a clean source tree and an API key through `SPIRE_OPENAI_KEY_FILE`), review them,
make one change to the prompt, rendering or memory, and log the version in
[log.md](log.md). The review is the `wh3-version-review` workflow
(`.claude/workflows/wh3-version-review.js`): a reviewer per episode reads the digest and
the prompts and replies around the turning points, three proposers each suggest one
change (tactics prompt, state and memory, order interface) with the version history and
the baseline in view, and three judges score them. While it runs, replay the same
version for two or three more episodes, and draft the next change in a git worktree: a
job stops if its source scope changes. The WH3 ledger
(`runs/twwarhammer3/llm-spend.jsonl`) is separate from Spire's, with its own $25 cap.
