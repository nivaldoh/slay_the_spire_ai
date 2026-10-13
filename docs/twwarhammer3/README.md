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
- A job (`battle/play.py`) launches the game, runs the custom battle steps it builds
  from the `--scenario` entry in `configs/twwarhammer3/scenarios.json` (each side's race,
  faction and units; no desktop input), plays episodes and restarts the
  same battle between them through the results popup's rematch button. Each episode
  writes `trace.jsonl` (every observation, prompt, reply and acknowledgement),
  `result.json` and `mod.log`; each finished episode appends a row to
  [results.csv](results.csv). Versions are logged in [log.md](log.md).

## Status (2026-10-13 08:20 local)

| Milestone | State | Evidence |
|---|---|---|
| 1 Mod loads | done | `runs/twwarhammer3/launch-m1/` |
| 1b Unattended custom battle | done | menu steps recruit both armies by double-click and start the battle; `runs/twwarhammer3/battle/*/menu.log` |
| 2 Roster readable | done | 5 v 5 units with positions, strength, fatigue, flags, targets in every observation |
| 3 Orders apply | done | attack, move (with facing) and halt through one unitcontroller per unit; acknowledgements carry the applied battle time |
| 4 Result | done | "lost" and "won" from the engine at VictoryCountdown, with both armies' true strength for evaluation |
| 5 Restart | done | rematch button and confirmation; 40 episodes in 14 jobs, none an infrastructure failure |
| 6 Scripted baselines | done | `attack_nearest`: 3 wins of 3 at about 345 s |
| 7 First LLM battles | done | v1: 1 win of 3 |
| 8 Autoresearch loop | running | [log.md](log.md): v2 0/3, v3 3/5, v4 1/3 (1/3 paused), v5 4/6, v6 5/6, v7 2/6 (reverted); v8-v11 on mirror battles, no mirror win yet with guns |
| 9 Several scenarios | done | `configs/twwarhammer3/scenarios.json`: each side's race is picked in the selector's popup; Khorne, Dwarf and Empire mirrors |

Results by version: `python -m twwarhammer3 stats`. With outcomes this noisy (a version's
battles swing between a clear win and a clear loss), three episodes rank versions only
roughly; `own_left` and `enemy_left` (true strength at the end) add a finer measure.

## What the first night showed (2026-10-13)

- The model can command a real-time battle through the mod: about one decision per 10 s
  of battle time, orders applied about 5 s after the state it saw, no invalid replies,
  about $0.01 per battle.
- The fixed script that sends every unit at its nearest enemy, walking, wins this battle
  every time. The model's early losses came from what it added: passivity (v1), retreats
  out of melee (v2), running everywhere and arriving tired, pairing its units off one to
  one, and above all leaving its lord to duel the enemy lord alone, or parking him while
  the enemy lord was nearly dead. Each version's prompt change targeted the costliest
  mistake the reviewers measured in the traces.
- Latency is not the gap: pausing the battle while the model thinks (orders applied 0.6 s
  after the state instead of 5.5 s) gave the same 1 of 3 for v4.
- The state must say what the game did with an order: the game retargets units on its
  own, and showing its choice as if it were the model's order made the model believe
  plans were running that were not (v6 fixed this; 5 wins of 6).
- Still weak in every version: the Skullcannon and the missile horsemen. An attack order
  only makes a unit with ammunition shoot, and their fire killed almost nothing.

## What the mirror battles showed (2026-10-13, second session)

Same army on both sides of the same map, the player starting north; 9 to 12 battles per
mirror. Wins and mean true strength left at the end (ours/enemy), from
`python -m twwarhammer3 stats`:

| Version | Empire (guns, cannon, knights) | Dwarfs (crossbows, catapult) | Khorne (melee) |
|---|---|---|---|
| attack_nearest | 0/2, 26/82% | | |
| v6 | 0/3, 21/69% | 0/3, 25/53% | 2/3, 34/25%; replicate 0/3, 38/64% |
| v8 guns | 0/3, 31/70% | 0/2, 30/76% | |
| v9 melee | | 0/3, 35/65% | 1/3, 26/47% |
| v10 shooters (`main`) | 0/3, 37/57% | 0/3, 42/68% | 0/3, 19/58% |
| v11 lords (reverted) | 0/3, 34/76% | | 0/3, 26/61% |

- With guns, crossbows or artillery on both sides, Luna lost every battle (0 of 11 in the
  Empire mirror, 0 of 11 in the Dwarf mirror), and so did `attack_nearest` (Empire, 0 of
  2). The losses follow one pattern: the AI's missile units and artillery shoot our units
  while they fight, and its missile infantry ends the battle untouched (66-67 of 68
  handgunners, 52-58 of 60 quarrellers).
- The game's AI stats modifier preference is 1.1 (pinned since the first night), so the
  AI's units are probably about 10% stronger: a mirror is not an even fight, and an even
  trade loses. Whether to play mirrors at 1.0 is an owner decision.
- The prompt changes traded the melee mirror for the gun mirrors. Margin (ours minus the
  enemy's strength left, in points): Empire v6 -48, v10 -20; Dwarfs v6 -28, v10 -26;
  Khorne v6 -8 over 6 battles (2 won; a replicate of 3 lost all), v10 -39 (0/3), v11 -35.
  Averaged over the three mirrors v6 and v10 are level (-28). Battles swing widely, so
  three per mirror and version separate little.
- Measured by the reviews over the traces: artillery killed about 2 men a shot at
  infantry in the open, 1 in 2 shots at missile infantry and 1 in 3 at crews; our missile
  units shooting enemy missile infantry killed about 1 man per 100 shots; our lord alone
  against the enemy lord lost health 3 to 8 times faster than he did.
- Harness gaps found: enemy units' targets never reached the state (llm.py rendered a
  field the mod never sent), there is no record of what a fire order killed, an attack
  order replaces a move (a shooter walks straight at a target out of range), and units
  with ammunition cannot be sent into melee. The decision delay grew from about 6 s to
  7-10 s as the prompt grew.

## Next

1. `main` runs v10 (v11 reverted after 0 of 6); v6's prompt (`6777a64`) is better in the
   Khorne mirror and on Khorne vs Dwarfs (5/6, untested with v8-v10). Find which v8-v10
   rule costs the melee mirror (v8's cavalry exemption from the lord gang-up and v10's
   fire doctrine for the Skullcannon and horsemen are suspects), with five or six battles
   per version. A shorter prompt is worth testing for think time.
2. Candidate on branch `wh3-fire-report` (`832b233`, built on v9): the mod publishes kill
   counts and enemy targets; an attack order shows shots fired and men killed since it
   was given, enemy lines show their target, our units show "attacked by e3 15 m rear".
   Ranked second by three reviews; untested in the engine (check that AI units report
   `current_target` and that `number_of_enemies_killed` returns numbers).
3. A melee mode for units with ammunition (`unitcontroller:melee`, `attack_unit`'s
   primary-attack flag) and an approach point for attack orders (go there, then attack),
   both proposed by reviews; untested in the engine.
4. The AI stats modifier (1.1) for mirror battles, and more mirrors (other races, maps).
5. Unmerged candidate `wh3-v4-info` (`aa1ece5`): compass directions, enemy missiles in
   reach and both armies' start points, for orientation errors the reviews still find.

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
