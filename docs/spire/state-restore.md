# Restoring the game to a saved state (investigation)

*Proposed 2026-10-23. The owner made this the highest priority within the Slay the Spire
work ([direction](../owner-direction.md)). Nothing is built or run yet. Everything below
is unverified until a check the owner agrees has passed
([AGENTS.md](../../AGENTS.md#verification-hard-rule)).*

**Goal.** Put the original game back into a recorded state, with the same RNG, then
choose differently from there. Training would use it for several rollouts from one state
(GRPO-style groups) and for counterfactual branches. Benchmarks would use it for fixed
situations that every model faces exactly.

**Sources.** A read-only research pass on 2026-10-23 covered five angles: mods, the game's
saves, replay determinism, simulators, and how restore would fit this repository. A
skeptic agent re-checked the first 12 claims of each angle (60 of 119), and one was
refuted. Facts the skeptics added themselves were not re-checked; two critics then
reviewed this page. Game facts come from disassembling the installed `desktop-1.0.jar`
(SHA-256 `cfad868a…`, the pinned build), from the 691 save snapshots of the
[2026-10-23 night](fullrun/log.md#2026-10-23-collection-night-qwen36-reasoning-off-harness-v102)
and from the traces in `runs/fullrun/`. The agents' reports and scripts are in
`runs/spire-restore-research-20261023/`, which has no backup. Third-party sources are
cited there by URL and commit; clones and game extracts were not kept.

## What the research found

**Where the game saves.** The game writes its autosave at three moments: on entering a room
(before the room is built), after Neow's blessing, and on the reward screen after a fight.
In-game Save and Quit writes nothing. Saves hold the deck, relics and their counters,
potions, HP, gold, map position, the upcoming encounter lists and the counters of seven
RNG streams. They hold no hand, draw pile, discard pile or monster state, no shrine list
and not every relic flag. So the game's own restore points are room starts and reward
screens, about 16 per run, never mid-combat. A community mod lists four cases where
reloading differs from continued play: a merchant after a merchant, shrine repeats,
event-fight reward screens and ? room odds.

**How RNG comes back.** Thirteen RNG streams live on the dungeon. Seven come back from the
saved counters: monster, event, merchant, card, treasure, relic and potion. Five are
rebuilt as `Random(seed + floor)` at every room entry, on a normal entry and on a load
alike: monster HP, AI, shuffle, card-random and misc. The map is rebuilt from the seed
per act. Event and potion-drop chances are saved too. So a room-entry restore should start
the room with the RNG the original visit had. That is expected from the bytecode and has
never been run. A reward-screen restore rebuilds the five per-floor streams from zero.
Draws made during the fight are then missing, so later draws on that floor can differ.
One example: Whetstone and War Paint from an elite reward use the misc stream.

**The interface cannot continue a run.** At the main menu the pinned CommunicationMod
1.2.1 offers only `start` and `state`; `key` and `click` work only inside a run. A
restore from a save needs a new command. daniel-ziegler's MIT fork of CommunicationMod
adds `resume` (commit `371caf0`). Several other mods load saves (Quick Restart, Run
Resumer, STSStateSaver), but none has a license, so only their technique can be reused.
[reset-probe.md](first-combat/reset-probe.md) already records the facts such a command
must handle: the availability check before dispatch, `loadingSave` and the menu fade.

**Replaying commands looks deterministic so far.** Many runs share seeds: RUNDEV1, RUNDEV2
and RUNDEV3 were played 13, 10 and 8 times across harness versions, QWENSMOKE1 twice.
Across 152 same-seed run pairs, observations were identical while the two runs' commands
agreed: 1,230 compared steps, 150 distinct states, zero differences once card UUIDs are
dropped. The prefixes are short, 2 to 33 commands, and none goes past floor 3. Wider
evidence agrees: every act map and boss matched per seed, and 331 combat starts with the
same floor and encounter (88 groups) had the same monster max HP and first intents. Card
UUIDs change on every launch, so any comparison must ignore them.

**Randomness no restore controls.** The game's libGDX `MathUtils` is seeded from the clock.
Gameplay uses found so far:
- Discovery and the Attack, Skill, Power and Colorless potions regenerate their choices from
  the card-random stream on every frame until a timer runs out. How many draws that takes
  depends on frame timing. Later draws in the same room can then differ; the next room
  entry rebuilds the stream.
- In the unmodded game, end-of-turn card triggers run in an unseeded shuffled order. The
  pinned BaseMod contains `ConsistentEtherealPatch`, which seeds that shuffle when its
  `basemod-fixes` setting is on. That setting defaults to on and our config file is empty,
  so the order is very likely seeded here; this comes from bytecode and is unchecked live.
- The Courier's shop restock is unseeded, but The Courier is locked in this profile.
- Act 3's Secret Portal joins the shrine list only after 800 s of play time. A replay runs
  faster than the model played, so its act 3 shrine list can differ.
- The Library's book text comes from `MathUtils`. It has no gameplay effect, but
  CommunicationMod exports it, so a strict comparison sees it.

The "unseeded card transform" path one agent reported is not reachable in the pinned jars.

**Profile state leaks into runs.** Seeded runs use the profile's unlocks. Ironclad
progress is 1,457 of the 1,500 needed for unlock level 4; the 2026-10-23 night added 38.
Level 4 adds three cards (Havoc, Sentinel, Exhume) to the pools, so replays of older
traces would likely diverge at their first card reward or shop. A replay that reaches the
death screen adds its score: DATA001 scored 100 and the long Luna run below 506, either
enough to cross. The Note For Yourself event reads and writes a profile preference.
Neow does not depend on the profile for seeded runs.

**The mid-combat restores found all come from mods that change the game.**
boardengineer's STSStateSaver copies all 13 streams in memory at a combat decision. It
does not restore the card-rarity and potion-drop pity counters or the relic, monster and
event lists, so rewards after the fight can differ between branches. It also removes six
potion types at startup, rewrites Discovery and about 20 selection actions, targets an
older build and has no license ([integration.md](integration.md#acceleration-candidates-considered)).
Undo the Spire builds on it for this exact build and ModTheSpire version and fixes many
gaps. It is GPL-3.0 and keeps the Discovery rewrite.

**Simulators.** `sts_lightspeed` (MIT, C++) is the only simulator found that loads the
game's own save and follows its RNG streams. It loads start-of-fight saves only: 243 of
the 691 snapshots. Branching is copying its battle state. Exact parity is claimed but
unproven: about 40 fix requests are open, several for cards in our snapshots. A patched
fork reports 490 matched real-game cases and still calls itself incomplete.

## Routes

| Route | Restore points | RNG | Needs | Main risk |
|---|---|---|---|---|
| A. Replay recorded commands from a seeded `START` | Any decision, mid-combat included | Same draws repeated; each step compared with the recorded observation | Python only, no new mod; about 10 s launch plus 0.9 s per command | Divergence after the effects above; deeper replays untested |
| B. Continue from an autosave snapshot | Room start and reward screen | Room start: RNG expected exact, unsaved state such as the shrine list may differ; reward screen partly reseeded | A `resume` command (fork commit or own mod), a JDK to build it, a new pinned jar | Changes the pinned engine; places files in the owner's profile |
| C. B to the room start, then A inside the room | Any decision | As B, then compared step by step as A | Both | Only worth it if A is too slow |
| D. In-memory save states (STSStateSaver, Undo the Spire) | Any combat decision | All 13 streams copied; pity counters and lists not restored | Two or three unlicensed or GPL jars | Changes gameplay even without a load |
| E. Simulator from a start-of-fight snapshot | Start of fights, then any copy | Claimed exact, unproven here | Building third-party C++ code offline; no runtime change | Parity gaps; not the real game |

JUDGEMENT: route A is investigated first, then B (assistant, 2026-10-23). A needs no new
mod and places no snapshot in the profile; like every run it still writes saves and
preferences. B or D first would test exact snapshot restores sooner. The plan rests on it.

## Plan

Each step has its check written first; a failed check stops the steps that depend on it.

1. **Offline, $0.** Build the replay plan from existing traces: for each chosen state, the
   commands up to it and the expected settled observations. Run the comparator on two
   same-seed traces that split, for example two RUNDEV1 runs, and confirm it reports the
   first difference where their commands split. From the pinned jars, settle whether a
   shorter act 3 shrine list changes the shrine picked, how Discovery's draws depend on
   frame timing, and which other event texts use `MathUtils`.
2. **Live replay check, route A.** Three launches, about 25 minutes of game time, no model
   calls ($0), in a window the owner names and only after the profile decision below.
   Before launching, copy `preferences/` aside and check that every `.backUp` exists. A
   replay driver on a local branch sends a recorded run's commands, stops at the first
   difference, and stops before the command that ends the run, so no score reaches the
   unlock progress. It writes to `runs/spire-restore-<name>/` outside `runs/fullrun/`,
   adds no results row, and records its branch commit and the profile before and after.
   - DATA001 (212 commands, floor 16) twice. Its 24 recorded snapshots also let the driver
     compare each autosave, timing fields aside, so hidden counters are checked.
   - The long Luna run (`llm-luna-v7-dev-20261012`, RUNDEV2, 881 commands, acts 1-3, died
     at the act 3 boss) once. It has no snapshots, so past act 1 only visible
     observations are checked. Unpaced, it reaches its first act 3 shrine (Purifier,
     floor 36) near 600 s of play time, while the original was far past 800 s.

   Pass: no difference, or a first difference where a listed effect can act. That means
   later in the same room after a Discovery-family pick, an end turn with two or more
   end-of-turn trigger cards, or the act 3 shrine roll. Any other first difference fails.
3. **Branch control, route A.** Three launches, each replaying to one combat state (about
   10 s plus 0.9 s per command). Take the recorded choice once and one fixed alternative
   twice. Each alternative continues with a fixed command list to the end of that combat,
   through at least one enemy turn and one draw. Pass: the recorded branch matches the
   trace, the two alternatives match each other, and they differ from the recorded branch.
4. **Route B, only with the owner's decisions below.** Add a `resume` command, remove any
   stale `.backUp` before placing a snapshot, and restore 6 to 8 chosen snapshots twice
   each (about 16 launches, 10 minutes). Pass: in both restores the first state equals the
   recorded observation at that point. Room-entry snapshots then replay the recorded
   commands as in step 2. For reward-screen snapshots, the only allowed differences are
   later same-floor draws from the per-floor streams, each named.
5. **Offline simulator parity, with the owner's approval to build third-party code.** Load
   the 243 start-of-fight snapshots in `sts_lightspeed`, replay each fight's recorded
   commands and report the first differing step. This measures act 1 parity on one
   model's fights. Using a simulator for training branches would need a parity threshold
   the owner sets, and fights from later acts.
6. **Exact mid-combat restore without replay.** Only if the owner judges route A too slow,
   using step 2's measured restore times; replaying to act 3 takes about 8 to 10 minutes.
   It means a mod in the runtime (D, or a small state exporter of our own), with a
   differential check that fresh seeded runs are unchanged with it loaded.

Proposed checks (not agreed): the step 2 replay parity, the step 3 branch control and
the step 4 restore comparison, each with the pass rule above. Until the owner agrees one,
a passing run is evidence, not verification.

JUDGEMENT: "same state" means identical settled observations with card UUIDs and The
Library's book text removed, plus identical autosave fields apart from timing (assistant,
2026-10-23). A stricter rule would compare hidden RNG positions mid-floor. Every pass
above rests on it.

## Owner decisions

- **Profile, before any further Spire game time.** Unlock level 4 is 43 points away, and
  a death screen adds the run's score. Freeze the profile at level 3, for example by copying
  `preferences/` aside and back around each job, or let it advance and tag each trace with
  its unlock state (`profile.json` records the unlock file hash). Owner's note
  (2026-10-23): "we might want to unlock things normally first in the game before enabling
  this". That means playing to the last Ironclad unlock (level 3 of 5 now) before restore
  work, so the pools stop changing. Traces recorded before that point would then not
  replay, so the restore checks would use runs recorded after it.
- **Route.** Replay only (A); a new jar in the pinned runtime (B, C or D), which also needs a
  JDK installed; or an offline simulator (E), which needs approval to build third-party
  code and a parity threshold.
- **Act 3 pacing.** Hold replays back so play time passes 800 s before act 3, as in the
  recording, or accept a different act 3 shrine list.
- **Randomness after a branch.** Training branches can keep the restored future draws (A,
  B) or get new draws after the branch point (D or E). The open-weight plan avoids
  revealing hidden futures.
- **Policy memory at a restored state.** The source run's notes and history, or none. This
  fixes what a fixed-situation benchmark measures.
- **Where branch runs are recorded.** The results register (which assumes runs start at
  Neow), a separate register, or only in exports.
- **Unlicensed mods.** Reuse their technique only, or ask their authors.

## Risks found on the way

- **Profile files are being emptied.** Preference files are often left empty: 25 of the 43
  data runs (26 of 44 with that day's smoke run) started with an empty `STSDataVagabond`
  (Ironclad statistics), which the game restored from its `.backUp` copy. All logs show
  41 such recoveries, plus 2 for `STSUnlockProgress`. The likely cause is the game being
  killed between deleting and rewriting a file. `STSDataVagabond` is 0 bytes on disk now,
  and `STSUnlockProgress` currently has no `.backUp`. This predates restore work and can
  affect any Spire run.
- **Steam Cloud.** Steam's app info lists the game's `preferences/` and `saves/` folders for
  Auto-Cloud; synced records so far hold only preferences. A save or preference left on
  disk would probably sync at the owner's next Steam-launched session.
- **Damaged saves.** If a save cannot be read, the game deletes it and, during a load,
  exits. If the main file is corrupt, the game sets it aside and silently loads the older
  `.backUp` instead. Edited or damaged snapshots must never be placed in the profile.
