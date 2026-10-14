# Total War: WARHAMMER III battles

Second game, started 2026-10-13. The question: can an API model (`gpt-6-luna`, low
effort, through `src/gameai/llm.py`) command an army in a real-time custom battle
against the game AI, with the delay between the state it saw and its orders
being issued to the engine measured and told to it, and can the autoresearch loop improve its
scaffolding? Campaign mode and model training come later.
[integration.md](integration.md) holds the verified engine facts; [guide.txt](guide.txt)
is the owner's modding guide that set the shape.

## How it works

Everything the game knows leaves it through a Lua mod, and every order enters the same
way. There is no external game API; the mod is the API.

- `src/twwarhammer3/mod/` is packed into `C:/wh3-agent/mods/twwarhammer3.pack` by
  `engine/pack.py` and loaded through a mod list the executable takes as its argument
  (`engine/runtime.py`). Four scripts: `script/_lib/mod/twwarhammer3_json.lua` (vendored
  rxi json.lua), `script/_lib/mod/twwarhammer3_ui.lua` (UI steps shared by the frontend
  and battle scripts), `script/frontend/mod/twwarhammer3_frontend.lua` (drives the menus)
  and `script/battle/mod/twwarhammer3_battle.lua` (observations, orders, result).
- The controller in WSL talks to the scripts through files in `C:/wh3-agent/bridge/`
  (`engine/mailbox.py` documents the messages): `session.json` enables the scripts and
  sets observation and decision intervals; `menu.json` carries frontend steps (find a UI component by
  id and click it, dump the UI tree, press a key, wait); `observation.json` is rewritten by
  the battle script every observation interval; `orders.json` holds one outstanding
  request (unit orders or a `restart` control). The scripts are inert
  without a session file, so the installed pack changes nothing in ordinary play.
- Real-time by design: the battle keeps running while the model thinks. Every request
  carries the observation it was based on; the acknowledgement carries the battle time at
  which the orders were issued or queued. `delay_ms` is measured per decision and goes
  into the next prompt. Battles always run unpaused at normal 1x speed, including
  diagnostic probes. The CLI has no pause or speed override; stale session settings
  requesting either are rejected.
- Decisions now start as soon as the preceding batch is acknowledged. `--interval-ms`
  defaults to **0**; a positive value explicitly adds battle time after application.
  `--observe-ms` controls state publication, independently of decision pacing. Traces
  include `since_previous_applied_ms` so that observation age and intentional pacing
  can be distinguished from model/application latency.
- Orders: `move` (position, facing, width), `attack` (auto/melee/ranged), `halt`,
  `behaviour` (fire-at-will, skirmish, guard/defend, spacing, formed attack), and
  `ability` (owned active ability, self/unit/ground target; unit `"army"` for an army
  ability). A move can be followed by queued moves and a final attack in one reply. Each
  acknowledgement identifies its one-based order index, including multiple orders for the
  same unit. Queue acceptance does not prove execution; the state labels it as the last
  submitted sequence. Friendly units show supported toggles and their state, width, the
  last requested attack mode and each active ability with its target type, magic cost,
  cooldown, readiness (ready, recharging with the seconds left, active), uses left and
  last issue time. Army abilities (Khorne's kill unlocks) show their target, radius,
  unlock cost and readiness, with the points the army has earned. Unit ability state
  comes from the UI context system; army ability readiness from the HUD button and its
  timer. Validation refuses an ability that is not ready. The state also gives the
  player's Winds of Magic pool/reserve.
  [Integration facts](integration.md#expanded-controller-interface-2026-10-13) and
  [ability state](integration.md#ability-state-through-the-ui-context-system-probed-2026-10-13)
  record the engine probes and their limits.
- Policies see dicts (`protocol.py`): friendly units in full, enemy units only while
  `is_visible_to_alliance` says the player can see them, plus the enemy roster as the
  custom battle screen shows it. `battle/scripted.py` has `hold`, `attack_nearest` and
  `probe_move` (the axis probe); `battle/llm.py` and `configs/twwarhammer3/` are the
  API-model policy and the autoresearch loop's editable surface. Since 2026-10-13 two
  more: `skills` (persistent per-unit skills run by a scripted executor on every
  observation) and `commander` (an API model setting those skills asynchronously, so
  units keep acting while it thinks). [controllers.md](controllers.md) describes every
  controller, how to compare them, and the researched designs not built yet.
- A job (`battle/play.py`) launches the game, runs the custom battle steps it builds
  from the `--scenario` entry in `configs/twwarhammer3/scenarios.json` (each side's race,
  faction and units, optionally the map; no desktop input), plays episodes and restarts the
  same battle between them through the results popup's rematch button. `--scenario
  random` (2026-10-13) draws a classic-battle map and each side's race from
  `configs/twwarhammer3/custom_battle.json` with `--seed` (recorded; drawn when omitted).
  It leaves the faction to the game, because it only changes banner colours, and fills
  both armies with the game's Autogenerate army button (13 units a side in the
  first draw, seed 2; the probe's single click filled a cleared Khorne army with 11).
  The draw is in the manifest's `scenario`; the armies the game generated are in each
  episode's roster. Rematches replay the same draw, so a job is one matchup. Funds, unit
  size (large), time limit (long) and AI difficulty (very hard) stay as the profile has
  them ([integration.md](integration.md#frontend-automation)). Each episode
  writes `trace.jsonl` (every observation, prompt, reply and acknowledgement),
  `result.json` and `mod.log`; each finished episode appends a row to
  [results.csv](results.csv). Versions are logged in [log.md](log.md).

## Current controllers

On `main`: the direct controller `llm` v15 (v10 tactical rules on the v13 interface of
continuous decisions and expanded controls), the `commander` v3, and the `skills`
executor v1.2 that the commander drives. v14 and commander v2 (`9bfee82`, `739ce9c`)
added ability readiness and army abilities, as above; v15 and commander v3 (2026-10-14)
add every battle type's objectives, the `build` and `reinforce` orders and the objective
rules ([battle-types.md](battle-types.md)), and v15 keeps a reply's valid orders when the
retries run out instead of ending the battle. `watch` follows a job beside the
game, and `play --show` puts each model reply in the advisor window. Latest results: on
the fixed `kho5-dwf5`, `skills` and the Luna commander v1 won 5 of 6 each; on three
paired random draws every controller lost all three
([log.md](log.md#random-battle-comparison-partial-2026-10-1314)).

## Milestones (2026-10-13)

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
| 8 Autoresearch loop | stopped | [log.md](log.md): v2 0/3, v3 3/5, v4 1/3 (1/3 paused), v5 4/6, v6 5/6, v7 2/6 (reverted); v8-v11 on mirror battles, no mirror win yet with guns |
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
| v12 v6 + v10 fire (reverted) | | | 0/3, 16/55% |

- With guns, crossbows or artillery on both sides, Luna lost every battle (0 of 11 in the
  Empire mirror, 0 of 11 in the Dwarf mirror), and so did `attack_nearest` (Empire, 0 of
  2). The losses follow one pattern: the AI's missile units and artillery shoot our units
  while they fight, and its missile infantry ends the battle untouched (66-67 of 68
  handgunners, 52-58 of 60 quarrellers).
- The game's AI stats modifier preference is 1.1 (pinned since the first night), so the
  AI's units are probably about 10% stronger: a mirror is not an even fight, and an even
  trade loses. The owner subsequently authorized testing 1.0 and 1.1 during benchmark calibration.
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

Current work is the owner's benchmark goal; [benchmark-progress.md](benchmark-progress.md)
tracks the evidence and [calibration-plan.md](calibration-plan.md) specifies the experiments.

1. Finish live acceptance of the terrain, AI-modifier and setup-failure paths. The b1
   five-controller rotation completed on one instance, with matched rematch starts and
   engine results for every controller, including an imported controller.
2. Select specialist challenges using the owner's [scenario recipe](scenario-recipe.md):
   anchor units, faction mechanics, difficult tactical choices and watchable battles.
   Screen cavalry/anti-large and caster-led prototypes before committing to repeated
   calibration at AI modifiers 1.0/1.1. Keep held-out variants out of tuning.
3. Run paired added-observation-age arms 0/6/10 s, unpaused at 1x, and report uncertainty.
4. Later resume the random-draw model comparison on seeds 264482191, 1355466036 and
   238913231, then compare larger models on the same declared scenarios. Broader battle
   types and offensive sieges need their remaining interfaces before benchmark admission.

The earlier tactical candidates remain unmerged and untested: `wh3-fire-report` and
`wh3-v4-info` predate the v13 interface and would need rebasing before evaluation.

## Other battle types (owner request, 2026-10-13)

Done for all nine on 2026-10-14 (overnight): [battle-types.md](battle-types.md) has one
minimal scenario per type (conquest, domination, free-for-all, ambush, chokepoint,
subterranean, minor settlement, siege, survival), the `mode` state that reports each
type's objectives (role, timeout winner, the game's objective text, capture points,
tickets, gates, supplies, building slots, reinforcement pool), the `build` and
`reinforce` orders, and the results. Engine facts:
[integration.md](integration.md#battle-types-probed-2026-10-14).

## Commands

```bash
uv run python -m twwarhammer3 play --policy commander --budget-usd 25 --scenario random \
    --seed N --output runs/twwarhammer3/battle/commander-luna-vN-rand-N-YYYYMMDD
uv run python -m twwarhammer3 play --policy llm --budget-usd 25 --scenario random \
    --seed N --output runs/twwarhammer3/battle/llm-luna-vN-rand-N-YYYYMMDD
uv run python -m twwarhammer3 play --policy skills --scenario random --seed N \
    --output runs/twwarhammer3/battle/skills-vN-rand-N-YYYYMMDD
uv run python -m twwarhammer3 play --policy llm --budget-usd 25 --scenario kho5-dwf5 \
    --episodes 3 --output runs/twwarhammer3/battle/llm-luna-vN-kho-YYYYMMDD  # diagnostics
uv run python -m twwarhammer3 watch [runs/twwarhammer3/battle/<job>]  # live, beside the game
uv run python -m twwarhammer3 play ... --show          # model replies in the advisor window
uv run python -m twwarhammer3 play --policy probe_abilities --scenario random --seed 4 \
    --output runs/twwarhammer3/battle/probe-abilities-...  # casts abilities when ready
uv run python -m twwarhammer3 digest runs/twwarhammer3/battle/<job>[/episode-0000]
uv run python -m twwarhammer3 stats                  # results.csv by policy, harness and mode
uv run python -m twwarhammer3 spend                  # runs/twwarhammer3/llm-spend.jsonl total
uv run python -m twwarhammer3 doctor                 # pins, preferences, running game, mod files
uv run python -m twwarhammer3 pack --list PACK       # entries of any pack; --extract PACK NAME
uv run python -m twwarhammer3 launch                 # build, install, run the game until Ctrl-C
uv run python -m twwarhammer3 menu --dump 4          # UI tree of the current screen (ui_tree.txt)
uv run python -m twwarhammer3 menu --steps steps.json  # click through components; tails menu.log
uv run python -m twwarhammer3 menu --battle --steps steps.json  # the same in a battle (mod.log)
```

`--model` (default `gpt-6-luna`) and `--effort` (default `low`) pick the API model for
`llm` and `commander`. The key comes from `OPENAI_API_KEY` or the file named by
`SPIRE_OPENAI_KEY_FILE`; the shared `gameai.llm` reads it for both games, so the
variable keeps Spire's name.

`launch` and `play` automatically skip startup videos. While WH3 is stopped, runtime
preparation sets `fe_game_intro_video_enabled false` in the existing profile and installs
`data/zzz_twwarhammer3_skip_intro.pack`. This small PFH5 movie pack auto-loads for every
launch, including ordinary Steam launches without the project's mod list. It overrides
the five splash clips and all 13 localized warning clips with a blank video; the main
cinematic (`gam_int.ca_vp8`) stays intact for the in-game viewer. Other preferences,
comments and line endings are preserved, and identical startup files are not rewritten.

`doctor` reports the installed startup pack's hash and effective preference without
changing anything. Deployment evidence is saved in `launch`'s `deployment.json` and
`play`'s manifest. Nothing sends desktop input; the first menu step still waits (up to
240 s) for the main menu. To reverse the skip, stop WH3, remove the generated movie pack
from `data/`, and set the preference back to `true`. The next project launch reinstalls
the skip. The blank clip's source and MIT license are in
`src/twwarhammer3/assets/LICENSE.twpatcher`.

Measured on 2026-10-13: main menu in 149.0 s before the skip and 17.7 s after (about
131 s saved in one comparison). A launch without the project mod list also showed the
menu by the 20.8 s screenshot. The initial static loading splash remains;
[integration.md](integration.md) records the evidence.

## The loop

As for Spire full runs, on paired random seeds: play the same `--scenario random --seed N`
draws with each version or controller being compared, one job per seed (a rematch
replays the same draw, so a deterministic controller such as `skills` plays each seed
once). Fixed scenarios are only for quick diagnostics. `play` needs a clean source tree
and, for the model policies, an API key ([Commands](#commands)). Review the battles, make
one change to the prompt, rendering, memory or executor, and log the version in
[log.md](log.md). The review is the `wh3-version-review` workflow
(`.claude/workflows/wh3-version-review.js`): a reviewer per episode reads the digest and
the prompts and replies around the turning points, three proposers each suggest one
change (tactics prompt, state and memory, order interface) with the version history and
the baseline in view, and three judges score them. While it runs, play more seeds with
the same version, and draft the next change in a git worktree: a job stops if its
source scope changes. Update Active work in [../state.md](../state.md#active-work) when
a job starts and when it stops. The WH3 ledger (`runs/twwarhammer3/llm-spend.jsonl`) is
separate from Spire's, with its own $25 cap.
