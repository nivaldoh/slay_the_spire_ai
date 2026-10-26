# WH3 checkpoint RL: implementation plan

2026-10-25, revised 2026-10-26. The plan an implementing agent follows to build reinforcement
learning from restored battle checkpoints with a reverse curriculum: start near a win, learn
to reach the engine's win from there, then start earlier. It plans one training method in
full, the simplest, and a shared structure that later methods plug into and are compared
through; the later methods themselves are not planned here (owner, 2026-10-26). It builds on
the research handoff [checkpoint-rl.md](checkpoint-rl.md) (read it first) and corrects it
where the code says otherwise. The handoff's JUDGEMENT markers stand; where this plan
proposes a different value for the same call, its marker names the handoff marker it
competes with, and the owner decides between them. Implementation (2026-10-26, branch
`wh3-checkpoint-rl`, under the owner's goal to implement this plan): stages 1–5 are coded and
run as [logged](log.md#2026-10-26-checkpoint-rl-implemented-and-run-stage-3-fails-the-policy-collapses); every
check here is still a proposal and nothing is verified under the agreed-method rule.
Every stage ends in a check whose pass rule is written before it runs; a stage starts only
after the owner has answered the decisions listed for it ([owner decisions](#owner-decisions)).

Written from the code at `34f485b`, the evidence in `runs/twwarhammer3/checkpoint-check-20261025c/`
and the register. Facts carry where they come from; anything without a source is a proposal.
Ten mapping agents checked the handoff against the code, and five review rounds (thirty
agents, each finding checked by a skeptic) checked the drafts of this plan.

## What is established and what is not

| Fact | Source | Consequence |
|---|---|---|
| A restore reproduces every native checksum up to the checkpoint tick and the Lua seed. The agreed Land check passed at `6fdb271`, the declared siege cases at `2e2acbe`. Lab runs outside the repository's checks saw restored battles end like their source and one chained save restore (log, 2026-10-25) | AGENTS.md, [checkpoints.md](checkpoints.md), [log](log.md#2026-10-25-battle-checkpoints-restore-exactly-through-a-fast-rebuild) | The restore up to the handover is the one verified piece; everything after it is new and unverified here |
| Engine tick N is battle time N × 100 ms (readings: tick 1200 → `time_ms` 120000, 1300 → 130000); the agent requires a 100 ms tick interval | `checkpoint-check-20261025c/restore-a/native/native.jsonl`; `checkpoint_agent.js` `handOver` | Decision points are declared as engine ticks; the runner checks the mapping per run |
| One restore launch: agent ready → menu steps 29 s → battle loaded 14 s → rebuild of 1200 ticks 6 s (about 60× until the last 50 ticks, which run at 1x) → handover; then 10 s wall per 100 ticks. Whole launch 131–133 s for 80 s of play, so about 52 s outside the live battle. The Land scenario's engine deadline is about 1,205 s of battle time (reading at tick 1200: 1,084.8 s remaining) | the three restores' `native.jsonl` wall times and file times; `game.log` "TIME TO FIRST FRAME: 15.97 s"; the source reading; `checkpoint_agent.js` `SLOW_DOWN_TICKS` | Per attempt about 52 s plus the battle after the handover at 1x; a run to the timer is about 23 minutes of wall time; budget launches, not decisions |
| The agent's `lua_at` hook runs Lua on the mod's own Lua state at an exact completed tick, on the battle thread, inside the agent's `session_step` hook; a Lua error or a non-JSON return there calls `fail()`; `run()` refuses `lua_at` after tick 1 up to and including the checkpoint tick (tick 1 is allowed). The agent's chunks see globals that files loaded by the game's mod loader set: the agreed check's readings call `twwarhammer3_json`, which a library file sets as a global, and the loader gives every mod file the same environment | `checkpoint_agent.js` `testHooks`, `evaluate`, `fail`; `checkpoint.run`; `check_wh3_checkpoint.py` `READING`; `twwarhammer3_json.lua`; the game's `lib_core.lua` `load_mods` (`setfenv(loaded_file, self:get_env())`, read from `runs/twwarhammer3/vanilla/`) | An order handed to the mod at an exact tick is possible without any transport, if the mod exports an entry point the same way (it exports none today; the handoff proposed dispatch through the hooks without noting this) and the entry point never raises |
| The bridge mod loads in a restore, starts at battle time 4,900 ms **during the fast rebuild** and, by its code, publishes `Deployed` observations from then on; its real-time poll accepts `orders.json` at any time; no observation field marks rebuild or handover. The stream has never been logged | restore `mod.log` ("[4900] started"); `twwarhammer3_battle.lua` `start`, `tick`, `observation`; `mailbox.py` | A mailbox policy attached naively plays during the rebuild; observations published during the fast part of the rebuild cannot be read completely; the only handover and fault signal is the agent's `native.jsonl` |
| After a checksum mismatch the agent sends one `error` row, resets the replay speed and stops reporting; the game keeps running as a replay that looks live, the mod still publishing. Every normal run ends with a `detached` row (reason `application-requested`) after the runner's `STOP`, and `tick` rows can follow `done` | `checkpoint_agent.js` `fail`; `checkpoint_frida.py`; the four `native.jsonl` (`tick` 2001, and 2002 in the source, after `done` at 2000) | Faults are read from the event stream at any time; the expected final rows are not faults |
| The mod ticks every 300 ms of battle time (`tick_ms` 250 configured; `applied_ms` ≡ 100 mod 300 in all 421 trace-logged acknowledgements of `screen1-wolves-attack-l3`), its grid anchored at its start (4,900 ms in every checkpoint run). It publishes on a tick once `observe_ms` has passed: with `observe_ms` 1000 and no requests every 1,200 ms (first `Deployed` observation at 5,200 ms in `screen1-wolves-hold-l1`), about every 19 ms of wall time during the rebuild against a 0.1 s reader poll; an acknowledgement forces a publication and restarts that countdown. The seq-0 `Loading` placeholder (time 0) and the result observation (published from the phase-change callback) are off the grid. Through the mailbox the delay from a basis observation to `applied_ms` is 300 ms in 34,645 of 35,041 acknowledgements (98.9%) in the `result.json` files of the 33 `screen1-*` episodes played with no added observation age (39 played; the six 5 s-age episodes show 5,400–6,300 ms), 600 ms otherwise | `twwarhammer3_battle.lua` `tick`, `apply_pending`, `finish`; the episodes' `result.json` and traces | With `observe_ms` at most 300 the mod publishes on every tick and acknowledgements cannot shift the schedule; through the mailbox identical attempts can differ by one mod tick; an exact-tick hand-over removes that, but the declared tick must be placed against the grid |
| No restore has run through a policy loop, received an order through the mod's apply path, or had its ending read by the repository's runner; `run_in_game` stops at a mandatory `stop_tick`, never reads `observation.json`, and its limits are constants (game 600 s, agent 560 s, wait 150 s + 0.1 s per tick); the agent sends `done` at `stop_tick` before any `saved` row of that tick | `battle/checkpoint.py`, `checkpoint_frida.py`, `checkpoint_agent.js` `testHooks` | Stage 1 adds exactly these pieces and measures them |
| Current `llm_rules` prompts on the two-unit `ksl-raiders-emp-halberds` scenario: 1,995–2,191 input tokens over 6 calls in 3 exchanges (`bench-b24-s1-qwen-medium-20261017`) and 1,998–2,815 over 84 calls in 81 exchanges (`bench-b24-s1-qwen-none-20261017`), OpenRouter's count for Qwen3.6 | those jobs' traces | Spire's 2,048-token cap (`MAX_PROMPT_TOKENS`) would reject them; a 0.6B model needs a compact rendering measured with its own tokenizer |
| After the SFT smoke, Qwen3-0.6B chose index 0 in 16 of 16 decodes | [posttraining.md](../posttraining.md#first-end-to-end-test-2026-10-17) | Candidate order is permuted and an index-0 baseline reported, or index preference passes as learning |
| `status` and `engine_ending` can disagree (a won battle with a late controller failure is `policy_failure`); `stats` and `export` read `status` | `play._drive`, `stats.row`, `export.py` | Reward is read from `engine_ending` only |
| Public observations carry fields that differ between launches of one engine state: the per-launch identifiers `job` (the run's directory name) and `battle` (`os.time()`-`os.clock()` at load), `seq`, and the mod's own memory, which a restore does not have: `orders` (the last acknowledgement), `dest` (only while the mod's own last order was a move), `attack_mode`, `command_queue`, `navigation`, and `last_issued_ms` of unit and army abilities. `enemy_roster`'s seen and `dead` flags are mod memory too, rebuilt in a restore from observations made during the fast rebuild, where Lua readings lag | `twwarhammer3_battle.lua` `observation`, `unit_record`, army abilities, `load`; `checkpoint.py` (`job=output.name`); restore `mod.log` battle ids; [checkpoints.md](checkpoints.md#limits) | The context the model reads is a declared projection without the identifiers and the memory fields; `enemy_roster` stays (it is what a player sees), and stage 1 checks that restores agree on it |
| 338 recorded public observations of `emp-handgunners-grn-savage-orcs` exist: 186 in `bench-b29-rifle-orcs-floor-attack-20261018`, 152 in `bench-b45-savage10-glm-low-l1-20261020`. All are `Deployed` with the spearmen (`f1`) and the handgunners (`f2`, at least 1,080 rounds) alive and one visible enemy (`e1`). Fields the playing controller set differ by job: `behaviours.defend` is false in 186 of 186 `bench-b29` observations and true in 150 of 152 `bench-b45` ones, and the units' `moving`, `idle` and target states differ too, and so do time, ammunition, men, health, morale, fatigue, magic and bearing values. Every `bench-b45` observation has a `bench-b29` observation with `f1` and `f2` each within 5 m (127 of 152 with their displacements summing to under 5 m) | those jobs' `trace.jsonl` `observation` events | The synthetic check (stage 3) is built from real observation shapes with no game time, with every rendered field except positions taken from one reference observation in both splits |
| Register: `emp-handgunners-grn-savage-orcs` (the Land check's scenario, defender, 1200 s timer) has 2 scored rows, both won (`attack_nearest`, `llm_rules` GLM); `ksl-raiders-emp-halberds` (attacker): scripted rows won 2 of 9, `llm_rules` won 1 of 7 scored | `docs/twwarhammer3/results.csv` | Neither shows yet that a mid-battle choice changes the outcome; the stage 2 audit answers that |

## Design

One primitive, used by every stage that touches the game: a **step run**. It launches the
game with the agent, plays a source battle or restores a checkpoint, logs every observation
it reads and every agent event, hands the mod at most one validated order batch at a declared
engine tick through the agent's exact-tick hook, takes private readings, saves checkpoints at
declared ticks, and ends at the engine ending or a fault. Every step run uses `observe_ms`
300, so the mod publishes on every one of its ticks. Source runs, branch audits and the
closed-loop check are schedules of step runs. Training and evaluation are offline: the model
never runs beside the game.

```
source battle (hold, or one declared injected batch) ──save_at S1..Sn──▶ checkpoint library
                                                                        (replay + record + sha256)
step run: launch → Replays → checked rebuild → restored ──▶ observations logged (seq, time_ms, hash)
          lua_at at tick T: return twwarhammer3_inject(json) → mod applies on its next tick → ack in
          the observation → … → engine ending or fault; native.jsonl watched throughout
          ▼
attempt.json (context hash, batch, ack, applied_ms, ending, restore evidence, status)
          ▼
audit table ──▶ task set ◀── synthetic generator          (label transforms for controls)
                   ▼
offline, game stopped: method (exact_table@1) → adapters → evaluate → compare; recount
                   ▼
closed-loop check: the trained choice executed by a step run, compared with its audit attempt
```

### Decisions the design rests on

1. **Dispatch.** Training actions reach the mod through the agent's `lua_at` hook at the
   declared engine tick `T`, with the label `inject` and the chunk
   `return twwarhammer3_inject([==[<json>]==])`.
   The mod's new export parses the message (`request`, `based_on`, `orders`) and sets
   `state.pending` to it, nothing else (it neither reads nor sets `last_request`); the mod's
   own `apply_pending` and `apply_order` run on its next tick and the acknowledgement appears
   in the observation as usual. The export never raises: its whole body runs under `pcall`
   and it returns the JSON string `{"accepted": true}` or `{"accepted": false, "reason": "..."}`
   (refused before `start()`, after `finish()`, while a request is pending, or on a malformed
   message), which the agent records as a `lua` event and attribution reads. The batch is
   validated in Python with `validate_orders` against the context before launch; the request
   id is declared in the plan; `based_on` is the context's `seq` in its own stream, a label
   the acknowledgement echoes and attribution compares with the declared value. The
   transport differs from live play (no file, no poll); the apply path, the Lua re-checks
   and the acknowledgement format are the same.

   **Grid rule.** The mod's grid is its start time plus multiples of `G` = 300 ms, the start
   read from `mod.log` (`[4900] started`) and every logged observation except `Loading` and
   the result checked to lie on it. `100 × T` must not be a grid time: when the hook and a
   mod tick fall in the same engine tick their order is unknown, so such a `T` is refused,
   never moved. The context of `T` is then the grid observation just before `100 × T`, and
   the expected `applied_ms` is the next grid time after it. With the grid at 4,900 + 300k ms,
   grid ticks are ≡ 1 mod 3; for a save `S` at a multiple of 300 ticks, `T = S + 2` gives a
   context at `100S + 100` (after the handover) and `applied_ms` `100S + 400`. Two attempts
   with the same batch at the same `T` are then the same battle tick for tick, and any
   difference is a fault the native checksums expose. Alternatives: a hold-until-time field
   in the mailbox message (a protocol and mod change plus a handover gate in the policy
   loop), or the mailbox as it is with the measured one-tick jitter recorded as noise.

   JUDGEMENT: dispatch — Claude, 2026-10-26: exact-tick injection off the mod's grid (δ 2,
   observe_ms 300), versus a mailbox hold field or the mailbox with recorded jitter.
   Determinism of every reward and the fault detection of every stage rest on this.

2. **Context, decision tick and continuation.** The **context** of a decision at `T` is an
   observation of the rung's reference stream, chosen by the grid rule; a rung's reference is
   a no-injection restore of it (one launch per audited rung). The context's `time_ms` must
   be later than the handover (`100 × S`), else `T` is refused. The context is hashed and
   rendered through `context_projection(public)`, which drops `job`, `battle`, `seq` and the
   mod-memory fields named in the facts table, so a logged view and a restored view of one
   engine state hash alike. The executing attempt's log must contain an observation with the
   context's `time_ms` and projected hash: a different hash there makes the attempt
   `injection_failed`, while no observation at that time (a reader miss, seen as a seq gap)
   makes it `infrastructure`. After the injection nothing is sent: the **continuation is no
   further orders**, so native orders and the game's own unit behaviour continue (what the
   `hold` policy does, without its request traffic). Alternatives: a scripted continuation
   such as `attack_nearest`, which re-orders every unit within a second of the injected
   batch, or a tick-1 Lua script; a context that keeps the dropped fields (then no context
   matches across launches).

   JUDGEMENT: continuation — Claude, 2026-10-25: no orders after an injection, versus a
   scripted continuation; competes with checkpoint-rl.md `candidate_task`. Every branch
   outcome and therefore every reward rests on this.

   JUDGEMENT: context_projection — Claude, 2026-10-25: the context drops launch ids, seq and
   the mod's memory fields, keeping enemy_roster; versus the full public observation. What
   the policy reads and whether contexts match across launches rest on this.

3. **Action space: a small public candidate set.** `candidates(context)` is a pure, versioned
   function. Templates are generated in a fixed order and a later template whose batch
   equals an earlier one is dropped and recorded: `noop` (an empty batch, still injected and
   acknowledged); `attack_nearest` and `rush_nearest` for all able units (the scripted rules,
   one batch each); `fall_back_<unit>` for each unit with ammunition (a move away from its
   nearest visible enemy by `fall_back_m` 60, the point clamped inside the public
   `terrain.bounds`); `charge_<unit>` for each unit of class infantry, cavalry, chariot,
   monster, lord or hero with `range` 0 (an attack with `run` on its nearest visible enemy).
   At most eight. By the template arithmetic the two named two-unit armies give five each
   before dedupe. Each candidate has an id, the exact batch, which must pass
   `validate_orders` on the context, and a one-line public description produced from that
   final batch by one function, `describe(batch)`, after dedupe; `describe` names every order
   field (unit, type, target, point, `run`), and a scored list whose descriptions are not
   pairwise distinct is refused. A candidate whose
   acknowledgement carries a result with `ok: false` is `injection_failed` with reason
   `refused` and the engine's error; in an audit it is removed from the rung's scored list,
   which is recorded with its own mapping hash, and `n` counts that list.

   **Orderings.** The model never sees the candidates in canonical order. One function,
   `slot_to_candidate(permutation, slot)`, maps a displayed slot to a canonical candidate and
   is the only mapping the loss, evaluation and `rl confirm` use. Each task carries its
   **evaluation orderings**: `K_eval` distinct permutations (8, or half of the `n!` orderings
   if that is fewer) drawn without replacement, seeded by the task hash, and stored in the
   task. Training draws `K` fresh permutations for every update, seeded by (task hash, update
   ordinal, k), only from the orderings outside that task's evaluation set (a draw inside it
   is rejected and redrawn), so a policy that fits the evaluation orderings has not been
   trained on them. Every record stores the permutations it used, and every reported quantity
   is given per permutation and as a mean with its spread, beside an always-index-0 baseline.
   Alternative: free-form orders, or other templates.

   JUDGEMENT: candidate_set — Claude, 2026-10-25: these v1 templates, fall_back_m 60, the cap
   of eight and seeded permutations, versus free-form orders or other templates; competes
   with checkpoint-rl.md `candidate_task`. What a win can be attributed to rests on this.

4. **Reward.** 1 for `engine_ending.result == "won"` (timer endings included, as the benchmark
   agreed on 2026-10-23), 0 for a loss or draw, read from the attempt's own ending; no reward
   of any kind for an attempt whose status is not an engine result. This keeps the handoff's
   `terminal_reward` marker. The acknowledgement's `applied_ms` must be strictly less than the
   result observation's `time_ms` (`ending_margin_ms` 0): the mod applies a pending request
   before it checks the engine's decision on the same tick, so an acknowledgement carried by
   the result observation itself is an action without effect and the attempt is
   `injection_failed`. A positive margin would exclude attempts whose action ends the battle
   quickly and so has reward meaning.

   JUDGEMENT: ending_margin — Claude, 2026-10-25: applied strictly before the result
   observation (margin 0), versus a positive margin. Which attempts near the ending keep a
   reward rests on this.

5. **The first method: `exact_table@1`.** If stage 1 passes, the battle after a checkpoint is a
   deterministic function of the injected batch, so the branch audit (stage 2) yields the
   complete reward table `r(c)` of a one-decision rung. The method minimises
   `−(1/K) Σ_p Σ_c π_p(c|x) r(c)` over the update's `K` permutations `p`, each `π_p` from its
   own rendering, averaged over the tasks of a batch: the exact expected reward, with no
   sampled draws and no launches beyond the audit. Tasks whose rewards are all equal are
   dropped from the batch; a batch with none left skips the optimizer step and is recorded
   `updated: false`. A table does not depend on the adapter, so it may feed successive
   updates, each recording the task set hash and the update's ordinal; how many updates a
   run takes is its declared budget. In RL terms this is a policy-gradient step on a
   verifiable reward (the engine's ending) with the expectation taken exactly instead of
   estimated from samples. Sampled methods are later methods
   ([later](#later-methods-not-planned-here)).

   JUDGEMENT: objective — Claude, 2026-10-26: exact expected reward on audited one-decision
   tables as the first method, versus a sampled policy-gradient method first (competes with
   checkpoint-rl.md `candidate_reinforce`). Launches per update rest on this.

6. **Model and rendering.** Qwen3-0.6B with a bf16 LoRA (the handoff's `local_model`; a
   plumbing stand-in, not the post-training student), a compact rendering
   `render_context(context, candidates, permutation)` under a declared token cap measured with
   the pinned tokenizer, listing the candidates as numbered lines `k: <description>` in the
   permutation's order, candidate completions `{"a":N}` plus one pinned EOS id, summed
   completion token log-probabilities, one temperature. The rendering prints, for each
   friendly unit, its nearest visible enemy and the distance in whole metres (the synthetic
   check's rule reads this). The handoff's policy contract applies unchanged; an adapter is
   measured only under its declared rendering. A **fresh adapter** is the declared LoRA shape
   with PEFT's default initialisation (so it scores as the base), seeded by `adapter_seed`;
   `rl train` with start `fresh` first saves it as `adapter-0000/` with its declaration, and a
   control, a repeat or a later method names that saved declaration. Alternative: the
   benchmark's `llm_rules` prompt.

   JUDGEMENT: rendering — Claude, 2026-10-26: a new compact rendering (its token cap is in
   training_settings), versus the benchmark's prompt. What the model can read and whether any
   number compares with the benchmark controllers rest on this.

7. **Source battles, ladders, rungs, curriculum.** A **root** is a lobby-started battle,
   identified by the name of its `checkpoints/<root>/` directory, which the `rl checkpoint`
   plan declares. A **ladder** is a list of save ticks of one root, latest first; a **rung** is
   one (root, tick). Save ticks are multiples of the root's `readings.every`, so the source
   carries a private reading at every save tick, and lie at least `late_margin_s` before the
   source's engine ending; the **late rung** is the latest such save; a record at or after the
   ending is unusable and refused. Every step run carries the root's `readings` declaration
   (the check's reading Lua, the same `every`), so it emits the handover reading and later
   readings. The source is played by `rl checkpoint` with the agent attached: by default no
   orders at all (`hold`), so the `noop` candidate at any rung reproduces the source's own
   continuation; if the hold source does not reach an engine win, one injected batch at a
   declared tick, built from a hold run's logged observation, is the alternative. The control
   is recorded in every record as `source_control`. The **curriculum** starts at the training
   root's late rung and passes a rung when, after a run of `U` updates on the training set
   that includes it, the adapter's mass on winning candidates there, under its evaluation
   orderings, is at least `θ`; training moves one rung earlier only then, never back; a rung
   that does not pass ends the run.

   JUDGEMENT: source_control — Claude, 2026-10-25: a hold source, else one injected batch,
   versus a mailbox-played source. Which battle states the rungs are and whether `noop`
   reproduces a win rest on this.

   JUDGEMENT: curriculum_rule — Claude, 2026-10-26: pass a rung at mass on winners θ 0.8 after U
   updates (U in stage4_check), versus a return-based or adaptive rule or other values. What
   "learned to win from here" claims rests on this.

8. **One structure for every method.** A method changes only the update rule. Everything else
   is shared and frozen by version: the task format, the scorer and rendering, the candidate
   builder and `slot_to_candidate`, the permutation rule, the optimizer construction,
   artifact save and reload, the records, the evaluation and the method-agnostic tests. The
   pieces:
   - **Task**: one context with its scored candidate list, mapping hash, reward per candidate,
     split, provenance (an audit table hash, or the synthetic generator's hash and draw seed,
     and any label transform) and collection cost (the launches behind it; 0 for synthetic
     tasks).
   - **Task set**: a file listing tasks by hash with their splits; its hash names it. Built by
     `rl tasks` from audit tables and the synthetic generator, with an optional label
     transform on the training split only (`shuffle_classes` with its seed, or
     `derange_first_loser`), recorded in every task's provenance; held-out tasks are never
     transformed. A held-out split is fixed when the set is built. Real tasks are split by
     root (with all its checkpoints) and by declared scenario family; synthetic tasks by
     template source job; a validator applies the rule of each task's provenance and refuses
     a sibling in another split.
   - **Method**: `name@version` plus a config, registered in `METHODS` in `battle/rl.py`; it
     implements `step(scorer, optimizer, tasks, permutations, config) -> update_record`. The
     first and only entry is `exact_table@1`.
   - **Run**: `rl train` takes a method, its config, a training task set (it reads its
     training split only), a start adapter (`fresh` or a saved declaration), `adapter_seed`,
     `order_seed`, `batch_size` and a budget `max_updates`. Each pass over the training split
     is shuffled with `order_seed` and cut into batches (a short last batch kept; a set
     smaller than `batch_size` is one batch). A run always takes its full budget; stage rules
     are decided by `rl evaluate` after it, never during it. Every update record lists the
     hashes of the tasks in its batch and the objective on its own training orderings before
     and after; adapters are saved at the start and the end only, and every update record
     carries the adapter tensor hashes before and after.
   - **Evaluation**: `rl evaluate` scores any adapter on any task set under each task's
     evaluation orderings, with the same metrics for every method: per task, the expected
     reward `Σ_c π(c) r(c)` (the mass on winners) and argmax accuracy (the share of evaluation
     orderings whose top slot maps to a candidate with reward 1); per split, the argmax
     accuracy at each ordering index across the split's tasks, with its minimum and maximum;
     the uniform, always-index-0 and majority-class baselines; the start adapter's values and
     KL from it. For every ordering it records the slot log-probabilities, the argmax slot,
     the candidate it maps to and the text of the numbered line at that slot, parsed from the
     rendered prompt string; per task it records the candidate with the highest
     ordering-averaged probability. It writes `eval-<adapter>-<task set sha12>.json` in the
     run directory, once (a repeat is refused), with the run's provenance copied from the
     update records; the start adapter's evaluation records 0 updates, no training set and
     itself as start adapter.
   - **Comparison**: `rl compare` prints evaluations side by side: method and version, config
     hash, start adapter, training task set, data used (launches behind the training tasks
     and their count), updates, wall time, and the metrics by split. It refuses to place
     runs side by side unless the evaluation task set, start adapter, rendering, candidates,
     temperature, `K_eval`, the permutation rule, the token cap and the evaluation version
     all match, naming the field. Its first use is the synthetic check's verdict (stage 3).
   - **Method-agnostic tests**: parametrised over `METHODS`, so a new method runs them on its
     first commit (stage 3). They are stated for exact methods; a sampled method restates
     each in expectation over a declared number of seeds when it arrives.

   JUDGEMENT: method_comparison — Claude, 2026-10-26: one frozen task set, start adapter, 8 eval
   permutations and metric set, by expected reward, argmax accuracy and data used; versus
   per-method metrics. What a later "method B beats method A" claim means rests on this.

### What is not built

No general RL framework, no PPO or critic, no training resume beyond keeping the last
complete adapter, no change to `checkpoint_agent.js` (if one becomes unavoidable it is its
own reviewed commit and the agreed Land check is re-run before any RL launch), no mailbox or
protocol change, no handover gate in `play._drive`, no live model beside the game, no report
or HTML integration, no rows in the committed benchmark register, no API model calls ($0), no
change to the benchmark definition, no free-form orders, no comparison with benchmark
controllers, no transfer or "less data" claim from the first results (launches are counted
from the start so a later comparison is possible; its baseline is not chosen here). Land
Battle only; other battle types' checkpoints are verified only for their declared cases.
Spire's RL code and test fixtures are not imported; six game-neutral helpers move to `gameai`
at the start of stage 3. Attempt, audit, task and update records are a new format outside the
export-row contract; nothing feeds `gameai.sft`, a dataset, a teacher or Tinker.

## Code changes

All runtime code sits inside `play`'s source scope (`src/gameai`, `src/twwarhammer3`,
`configs/twwarhammer3`), so it is committed before any launch and an edit stops a running
WH3 job; an edit under `src/gameai` stops a running Spire job too. Draft in a worktree
outside `/tmp`. Each module stays small; reuse before adding.

| Stage | Module | Change | Tests |
|---|---|---|---|
| 1 | `mod/.../twwarhammer3_battle.lua` | `local function inject(text)` with the contract of decision 1, exported as `twwarhammer3_inject = inject` at the end of `load()` after the session check, so it exists only in an enabled battle and the lupa loader finds `inject` by name. Nothing else changes; the pack hash changes | lupa tests: a valid message becomes `state.pending` and `apply_pending` consumes it unchanged with the given request id and `based_on`; malformed JSON, missing fields, not started, finished and already-pending each return `accepted: false` with a reason, raise nothing and leave pending unchanged; the existing Lua tests pass |
| 1 | `battle/checkpoint.py` | **`episode(plan)`**: the one launch function for a source (`plan["scenario"]`) or a restore (`plan["checkpoint"]`). It runs a watcher thread over `native.jsonl` from its first byte and a reader over `observation.json` that logs every observation it reads with its seq gaps; takes plan-field limits (`game_timeout_s`, `agent_seconds` passed to `checkpoint_frida.py --seconds`, `episode_timeout_s`, `start_timeout_s`), the session's `observe_ms`, the root's `readings` and an optional `stop_tick`. It ends at the first of: the result observation (it then waits, bounded, for the `saved` rows of declared saves before the result's tick and records later saves as not reached), `done`, a fault, a limit. Before launch it refuses a missing Frida venv, a save name present in `replays/` or among the bystanders, a `T` on the grid or with a context before the handover, and a plan whose limits cannot contain the rung's `remaining_ms` plus the measured overhead and a margin. It moves every replay it saved into its output in its own `finally`. `run` and `run_in_game` become thin wrappers so the agreed check is unchanged. **Library**: a record = the agent's five fields + replay sha256 (taken after the source game closed) + the source run's path, `source_control`, scenario key and resolved scenario sha, exe, pack and agent sha256, `remaining_ms`, the source's `engine_ending`, the mod's start time and `G`; identity and refusal are the exe, pack and agent hashes and the replay hash (`source_revision` is recorded, not refused); the game-folder copy is `<name>-<sha12>.replay`, the agent config's `name` is the record's name, and `only_replay` gets the file's stem; a record at or after the source ending is unusable. **`restore_episode(record, plan)`** copies the replay in, checks its hash, runs `episode` inside `only_replay` (unchanged), and in its own `finally` around it re-hashes and removes the copy, then writes `attempt.json`. **`compare`** keeps its existing fields computed exactly as now (the recount of `checkpoint-check-20261025c` still gives 2,001 ticks and 699 mismatches for `changed`); new fields add observation sequences, endings, and `ticks_uncompared` and `readings_uncompared` counts, compared up to the earlier engine-ending tick. The reading Lua moves here as `READING_LUA`; the check script keeps the name `READING = checkpoint.READING_LUA` with the same bytes, so the siege check's `land.READING` still works | record and refusal tests; watcher and status tests on synthetic streams, replaced by slices of the stage 1 logs once they exist; comparator tests including the recount; the agreed Land check must still pass unchanged |
| 1 | `battle/play.py` | Extract `public(observation, scenario)` and `engine_ending(observation)` from `_drive` and use them there; `context_projection(public)` beside them; no other change | the existing play tests unchanged; sentinel tests on `public()` and the projection |
| 1 | `tests/twwarhammer3/check_wh3_restored_episode.py` (proposed check) | The stage 1 live check: plans, `assess`, `checks.json`, `--recount`, following `check_wh3_checkpoint.py`; it writes its source records through the `rl checkpoint` code under `runs/twwarhammer3/rl/checkpoints/<root>/` | pass-rule tests on synthetic and sliced logs with the negative cases |
| 2 | `battle/candidates.py` | `Candidate`, `candidates(context)`, `describe(batch)`, `CANDIDATES_VERSION`, the dedupe rule, mapping hash, `slot_to_candidate` and the permutation rule | purity, validity, uniqueness, hidden-field sentinels, descriptions, the displayed-slot test |
| 3 | `src/gameai/lm.py` | Move unchanged except a lock-path parameter and a public name: `candidate_log_probs`, `normalized`, `sample_index`, `tensor_hash` with its `_json` helper (same bytes; `tensor_sha256` stays in Spire), `verify_adapter_tensors`, `gpu_lease(path)`. Each Spire home module imports its names back: `spire.language.policy` re-exports `candidate_log_probs`, keeps `GPU_LOCK_PATH` and a wrapper `gpu_lease()` that passes it at call time, and keeps `_verify_adapter_tensors` as an alias; `sampling` re-exports `normalized` and `sample_index`; `training` re-exports `tensor_hash` and `_json`. Spire code, scripts and the tests that monkeypatch `policy.gpu_lease` or `policy.GPU_LOCK_PATH` are unchanged; WH3 uses the same lock path. Lazy torch imports | the Spire language tests pass under `--extra llm`; the moved hasher reproduces a recorded digest |
| 3 | `battle/rl.py` | `render_context` and the token-cap check; `CandidateScorer` (scores per permutation, normalised distribution, the full behaviour record); tasks, task sets, label transforms and the synthetic generator; `METHODS` with `exact_table@1`; the optimizer construction; artifact save and reload check; evaluation and comparison; reward extraction from `attempt.json`; update records; `recount` (which also prints the report lines); the declaration schema. Split into modules when a second method arrives, not before | the numerical, method-agnostic and record tests below |
| 1–4 | `__main__.py` | `rl checkpoint` (a source step run with `save_at` and readings; writes library records), `rl audit` (a declared set of step runs plus a named or new reference per rung; writes `table.json`), `rl tasks`, `rl train`, `rl evaluate`, `rl compare`, `rl confirm` (the closed-loop check), `rl recount`; each a separate process; game phases (`checkpoint`, `audit`, `confirm`) refuse while the GPU lease is held, model phases (`train`, `evaluate`, the scoring part of `confirm`) refuse while a game process exists (`runtime.running_pids` for WH3, `conflicting_games` for Spire) | CLI refusal tests with real subprocesses holding real locks |

Every `rl` phase runs under `uv run --locked --extra llm` with lazy torch imports, so game
phases never initialise CUDA; subprocesses use `sys.executable`; the manifest records the
lock hash and the installed torch version. `rl confirm` scores first, exits its model
process, checks that no CUDA process remains, then launches the game.

### Data flow

| Command | Reads | Writes |
|---|---|---|
| `rl checkpoint PLAN` | the root's name, a scenario, `save_at` ticks, `readings`, `source_control`, limits | `checkpoints/<root>/source/` (the run: `manifest.json`, `native/`, `observations.jsonl`, `attempt.json` with the ending, the mod's start time and `G`) and one `record.json` + `<name>-<sha12>.replay` per usable save |
| `rl audit PLAN` | records, the rung list, each rung's named reference (a no-injection restore attempt, run first when the rung has none), `CANDIDATES_VERSION`, repeats, limits | `audits/<name>/attempt-NNNN/` (each a step run: `manifest.json`, `native/`, `observations.jsonl`, `attempt.json`) and `table.json`: per rung the reference, the shared context hash, the scored candidate list and its mapping hash, per candidate its batch hash, description, attempt path and hash, `applied_ms`, status, ending and reward, refused candidates, per-status counts, launches used |
| `rl tasks PLAN` | audit tables by hash and/or the synthetic generator's declaration (templates, field normalisation, class balance, draw seeds, counts, rule), the split rule, an optional training-split label transform | `tasks/<name>.json`: tasks with contexts, scored candidate lists, mapping hashes, reward vectors, splits, provenance and collection cost |
| `rl train PLAN` | a training task set by hash, the method and its config, the start adapter (`fresh` or a declaration), `K`, temperature, `adapter_seed`, `order_seed`, `batch_size`, `max_updates` | `runs/<name>/update-NNNN.json` (the batch's task hashes, its permutations, behaviour distributions before and after, loss, gradient norm, first-order prediction, KL, adapter hashes before and after, the objective on its training orderings before and after, the task set hash and ordinal) and `adapter-0000/` and the final adapter with their declarations |
| `rl evaluate ADAPTER TASKS` | an adapter declaration, a task set, the run's update records | `eval-<adapter>-<task set sha12>.json` in the run directory: the metrics of decision 8 per task, ordering and split, slot log-probabilities, argmax slots, mapped candidates and line texts, the averaged choice per task, the run's provenance |
| `rl compare EVAL...` | `eval-*.json` files | a table on stdout, or a refusal naming the mismatched field |
| `rl confirm PLAN` | an adapter and its `eval-*.json` for the rung's task set, the true audit table by hash, a rung | a step run under `confirms/<name>/` and `confirm.json` with the pre-launch checks and the four clauses of the closed-loop check |
| `rl recount DIR` | any of the above | `recount.json` beside it: every reported number re-derived, with the checker's hash and the input hashes; the report lines on stdout |

Evidence goes to `runs/twwarhammer3/rl/`; add it to `runs/README.md` when it exists.
Adapters and records never live inside the source scope.

## Stages

Launch counts are what the pass rules need. One attempt costs about 52 s plus the battle
after the handover at 1x; a rung's worst case is its timer bound (`remaining_ms`), which the
limits must contain, while its typical cost is the source's ending time. All game time
needs an owner window; none of it spends API money. Stage 3 needs no game data; its code
needs stages 1 and 2's code (`public()`, `context_projection`, `candidates.py`), not their
game runs, so it can be built while stages 1 and 2 wait for a game window. Stage 4 needs
both.

### Stage 1: step run, library and the first live check

Build the stage 1 rows of the table. The watcher requires `restoring` and `restored` with
the record's name and tick and no `error`, `frida_error` or `detached` row before them. A
fault row after them and before the attempt's end makes the attempt `restore_fault`, except
an `error` row at the injection tick with no `lua` event for that tick before it (the export
missing or raising gives the message `Error: Lua inject: ...`, a non-JSON return a
`SyntaxError`), which makes it `injection_failed` with the message. Rows are placed relative
to the end by their position in `native.jsonl` (an end at the result observation is placed by
the latest `tick` row present when the reader logged it); `frida_error` rows carry no tick.
After the end, `tick` and `reading` rows are expected and ignored, and so is the final
`detached` with reason `application-requested`; any `error` or `frida_error` row after the
end, or any other `detached`, is recorded as `late_fault` beside the status. The live clock
ratio is measured from the first observation logged after `restored`. The agreed checks ran
with `observe_ms` 1000; stage 1's restores are the first evidence at 300, and the overhead
the limits check uses is taken from their measured times.

Attribution of an injection is a function with one test per clause: the attempt's log holds
an observation with the context's `time_ms` and projected hash; the `lua` event for the
injection says `accepted: true`; the acknowledgement in a later observation carries the
declared request id and `based_on`; its results count equals the batch length and every
result is ok (else reason `refused`); `applied_ms` equals the expected grid time (decision 1)
and is equal across repeats; `applied_ms` is strictly less than the result observation's
`time_ms`; the attempt's native checksums equal the reference's up to `applied_ms` (a
difference before it is a fault), and the first divergent tick after it is recorded, an
attempt that never diverges being recorded `no_effect` (by determinism its reward equals the
reference's, and it is not a failure); within `witness_window_ms` after `applied_ms` each
ordered unit shows the ordered `target` (attack), a `dest` within `witness_dest_m` of the
ordered point (move) or no `moving` state (halt), a unit whose context already showed that
value being recorded `witness: unchanged`; for `noop`, zero results and no divergence from
the reference. A failed clause gives status `injection_failed`, no reward, the clause named.

Live check (proposed), eleven launches on `emp-handgunners-grn-savage-orcs`, the Land check's
scenario, every run with `observe_ms` 300, the source run's limits about 1,400 s (a hold
source may run to the timer, about 23 minutes):

1. One hold source run, through the `rl checkpoint` code, to its engine ending: `save_at`
   every 300 ticks from 600 to the timer bound, readings every 100 ticks, observations
   logged. Pass: an engine ending read from the result observation with `mod.log` agreeing;
   a replay for every save before the ending, later saves recorded as not reached; every
   logged observation except `Loading` and the result on the grid (start from `mod.log`,
   `G` 300); the hashes of every file in the game's `replays/` folder recorded before and
   after (a changed save file is a finding, not a pass); whether `tick` rows continue after
   the result recorded as a measured fact. The late rung is the latest save at least
   `late_margin_s` before the ending.
2. Three no-injection restores of the late rung to the ending. Pass: from the first
   observation after the handover on, identical sequences of (seq, time_ms, projected hash),
   `enemy_roster` included, with no seq gap in any of the three (a gap is a reader miss, a
   finding about the reader); identical native checksums to the ending; identical endings;
   the observation at `100S + 100` (the default context) in all three logs; observations
   read during the rebuild logged and counted, not compared; no fault; the replay copy's
   hash unchanged after each run; the rebuild's wall time and the launch overhead with
   `observe_ms` 300 recorded. The restores are also compared with the source after the
   handover (checksums, projected observations, ending) and the result is reported. Any
   difference is a finding to explain, never an exclusion added to pass. The first restore
   is the late rung's reference.
3. Two identical attempts injecting one `attack_nearest` batch at `T = S + 2` (context at
   `100S + 100`, expected `applied_ms` `100S + 400`), and one attempt injecting a single move
   of the handgunners 60 m directly away from the nearest visible enemy, clamped inside
   `terrain.bounds`, computed from the same context by the check. Pass: every attribution
   clause holds; the two identical attempts match each other on every checksum and
   observation hash to the ending; the move attempt shows its `dest` witness and diverges
   from the reference after its `applied_ms` and nowhere before.
4. The agreed Land check re-run unchanged (four launches), since the mod changed. The
   AGENTS.md rows then read "passed at `2e2acbe`/`fbdba3b`; runtime changed since" (siege) and
   "passed at `45fe7b0`; runtime changed since" (scripted team; its "unchanged since" is
   already stale after `4592a54`); whether to spend the siege check's 15 launches or the team
   check's four is the owner's decision. The mod and `play.py` change is logged as a harness
   version, and tactic-card cells that span it are starred by the pack hash.

JUDGEMENT: stage1_check — Claude, 2026-10-25: these eleven launches and pass rules, versus
the handoff's live checks; competes with checkpoint-rl.md `verification_plan`. What stages 2
to 4 may build on rests on this.

Slices of these logs become the fixtures under `tests/twwarhammer3/checkpoint_rl/`; until
then the watcher and comparator tests use synthetic streams built in the same shape.

### Stage 2: candidates and the branch audit (scripted, no model)

Write `candidates.py`. Declare the training root before the audit. Default audit: the late
rung of the training root, every candidate once, one repeat of one candidate as the
determinism spot check, and the rung's reference (stage 1 step 2's first restore, named in
the audit plan): about six launches on the late rung, seven on a rung without a reference.
Pass rule: every attempt reaches an engine ending inside the limits with its cause recorded;
the repeat matches its sibling tick for tick; every candidate either applied or is
`injection_failed` with reason `refused`; the rung has at least one winning and one losing
candidate in its scored list. A flat rung is reported and not trained on; expanding to
earlier rungs or more repeats is declared before it runs and reported whole, so a tick
search is visible. Output: `table.json` with the shared context (all attempts of a rung must
carry the same context hash; unequal hashes block the rung). The owner reads the table
before stage 4.

### Stage 3: the method structure, the first method and the synthetic check (no launches)

Move the helpers to `gameai/lm.py`, then write `rl.py` in this order, each piece with its
tests before the next: rendering and scorer; tasks, task sets and label transforms;
`exact_table@1`; evaluation and comparison. Then measure, game stopped: load the base and a
fresh adapter, render and score a sample of synthetic contexts under their evaluation
orderings twice, and record two repeat deviations: of the slot log-probabilities (it sets
the reload tolerance) and of the objective (it sets the first-order threshold); also token
counts against the cap, CUDA peak allocated and reserved, process RSS, WSL `MemAvailable`,
Windows free memory, scoring and update times; one toy update, save, reload, compare.

**Method-agnostic tests** run on a CPU toy model whose configuration is copied from the
Spire RL tests into the WH3 test (no Spire import), with a WH3 toy scorer built on
`CandidateScorer`: the prompt is one context token, and the completion for displayed slot
`k` is the token of the canonical candidate `slot_to_candidate(p, k)` followed by EOS. The
toy's distribution over candidates is therefore the same under every permutation, and a
method that maps slots to candidates wrongly sends its reward to the wrong candidate. The
tests use the cycles (1,2,0) on three candidates and (1,2,3,4,0) on five, whose squares
move every candidate (the `p.index(k)` error credits the candidate `p∘p` maps the rewarded
one to), and their oracles are hand calculations and stated contracts:

- **Direction:** a positive reward on one candidate raises its probability after one small
  step; reversing the rewards from the same start lowers it.
- **No signal:** equal rewards change neither the adapter nor the optimizer state, after a
  nonzero step has populated the optimizer's moments.
- **Overfit one task:** on one toy table, the expected reward reaches 0.95 within 200 steps
  at the test's learning rate.
- **State dependence:** two contexts with different context tokens reward different
  candidates; after training, each context's argmax is its own winner under every
  evaluation ordering. Control: the same contexts with their rewards exchanged teach the
  exchanged answers.
- **First-order agreement:** for every step whose predicted change (the objective's gradient
  times the actual adapter change) exceeds 1e-6 (the toy scores deterministically on CPU),
  the measured change of the objective has the same sign.
- **Mapping control:** a copy of the method that uses `p.index(k)` where
  `slot_to_candidate` uses `p[k]` fails the direction and overfit tests under both cycles.

`exact_table@1` also gets its own oracle tests: its gradient equals a hand computation of
`−(1/K) Σ_p Σ_c π_p r` for `K` = 1 with (1,2,0) and for `K` = 3 with (1,2,0), (0,2,1) and
(1,0,2) on three candidates (a set not closed under inversion), the recorded loss equals the
hand value, and a batch whose tasks all have equal rewards is recorded `updated: false` with
no optimizer step.

**The synthetic check** (proposed): can this model, rendering and method learn a choice that
depends on the state, before any game data is spent? Templates are the 338 recorded public
observations of `emp-handgunners-grn-savage-orcs` (the proposed training root's scenario;
another root needs its own synthetic declaration), passed through `public()` and
`context_projection`. Before any edit, the generator replaces every field the rendering prints
except the units' `x` and `z` (time and countdown, men, health, ammunition, morale and its
effect, fatigue, every unit's state flags and `target`, `behaviours`, bearing, magic,
abilities, the enemy's state) with its value in one declared reference observation, the
first `bench-b29` observation, in both splits; so a synthetic context carries the template's
friendly positions and the generated enemy position, and nothing else differs between
tasks. It then draws the class with probability one half, and the distance `d` uniformly
within that class's band, 20–90 m or 110–300 m (a 20 m band around the boundary is left
out). It moves the enemy to distance `d` from the handgunners at a seeded bearing,
rejecting points that `terrain.bounds` would clamp, and rebuilds the candidates from the
edited context. Every draw comes from a stream keyed by (split, task index). The rule: if
`d` < 100 m, `fall_back_f2` has reward 1, otherwise `attack_nearest` does; every other
candidate has 0. Training tasks come from the `bench-b29` templates (200 tasks), held-out
tasks from the `bench-b45` templates (100 tasks).

Tests the generator must pass first: every rendered text states the handgunners' nearest
enemy and its distance; each synthetic context differs from the reference observation only
in the units' `x` and `z`, with no added key; two renderings of one template with the enemy
on either side of 100 m at the same bearing differ only in numeric tokens; no rendered field
value other than positions and distances occurs in one split only; no held-out task repeats
a training task's rounded distance and bearing on a template whose `f1` and `f2`
displacements from it sum to under 5 m.

Train `exact_table@1` from a fresh adapter in batches of 16 for 300 updates. The verdict is
read from `rl compare` of the trained adapter, the control and the start adapter on the
held-out split. Pass rule: the held-out argmax accuracy is at least 0.9 at every evaluation
ordering index (its minimum over indices), against a majority-class share of about 0.5,
which is reported beside it with the always-index-0 and start-adapter values. Control, with
the same settings and the same start adapter: the training split's rewards reassigned by
`shuffle_classes` and evaluated on the true held-out rule; its maximum over evaluation
ordering indices must stay at or below the held-out majority-class share plus 0.1. A
failure is classified before anything changes: training-split accuracy below 0.9 is a
budget or optimisation finding, after which one declared re-run with a larger budget or
learning rate is allowed and both runs are reported; training-split accuracy at or above
0.9 with held-out accuracy below it is a generalisation finding, which stops the plan
before stage 4. A pass shows the stack can learn a one-feature state-dependent rule from
rewards; it says nothing about battle tactics.

JUDGEMENT: synthetic_check — Claude, 2026-10-26: 100 m rule, balanced classes, 200/100 tasks
split by job, 300 updates, pass 0.9 at every eval permutation, control at majority + 0.1;
versus another rule or thresholds. Whether stage 4 starts rests on this.

Stage 3 pass rule: every numerical and method-agnostic test and its negative control pass;
every reload reproduces the scores within the measured tolerance; the generator tests, the
synthetic check and its control pass; `rl recount` reproduces every number without a model.

### Stage 4: the first method on the audited rung, overfit and closed loop (2 launches)

Build the training task set from the stage 2 table (one task: the late rung). Train
`exact_table@1` from a fresh adapter on that one task.

**Overfit check:** after a run of `U` updates, `rl evaluate` on the rung's task shows the mass
on winners averaged over its evaluation orderings at `θ_fit` 0.95 or more and the argmax
under every evaluation ordering a winning candidate; every update satisfies the first-order
agreement rule against the stage 3 objective repeat deviation; every reload reproduces the
scores. Training orderings exclude the evaluation orderings, so passing requires reading the
candidate lines, not memorising positions. This shows the method moves this policy where the
audited reward points on a real game context. A failure is classified from the records: the
objective on the last update's own training orderings below `θ_fit` is a budget finding;
training orderings fitted but evaluation orderings not is a finding about the model or the
rendering (it fitted positions). The closed-loop check is not run on an adapter that has not
passed.

**Closed-loop check** (proposed): `rl confirm` reads the true audit table by hash and the
adapter's evaluation file for the rung's task set. Before any launch it refuses unless the
loaded adapter's tensor hashes equal its declaration; its slot log-probabilities under the
evaluation orderings reproduce the evaluation file within the reload tolerance; the chosen
candidate (the highest ordering-averaged probability, mapped by `slot_to_candidate`) equals
the evaluation file's; the evaluation file shows the overfit check passed; and the chosen
candidate's reward in the true table is 1 (for the negative control below: it is the
deranged target). It renders the rung's scored list from the table, whose mapping hash must
equal the training task's. Then it injects the chosen candidate's batch, rebuilt from
`candidates(context)`, in one step run at the audit's `T`. Pass, four clauses:

- (a) For every evaluation ordering, the line text at that ordering's argmax slot, parsed from
  the rendered prompt string, equals `describe(batch)` of `slot_to_candidate(p, argmax)`
  (the text does not come from the mapping code, so a slot-to-candidate bug shared by
  training, evaluation and confirm fails here); and the executed batch's hash equals the
  table's batch hash for the chosen id (an id-to-batch mismatch fails here).
- (b) The attempt reproduces the audit attempt with that batch hash tick for tick, with the
  same `applied_ms` and ending (an execution or determinism fault after training fails here).
- (c) The table's reward for that id equals the reward from that audit attempt's
  `engine_ending` (a table built wrong fails here).
- (d) The reward read from the live attempt's ending is 1.

Given the overfit pass, (b), (c) and the pre-launch checks, (d) is predicted before the
launch; the launch confirms that the trained choice, executed through the real path,
reproduces its audited win. **Negative control**, one more launch: from the same start
adapter, train on the `derange_first_loser` task set (the first losing scored candidate in
canonical order gets reward 1, every other candidate 0). This run must pass the overfit
check on that wrong target before its launch is spent; `rl confirm` on it, reading the true
table, must then pass (a) to (c) and fail (d). Its (d) is also predicted, since the target
loses by construction; what the launch adds is (b) on a losing batch and (d) read from a
live losing ending, so the live path is seen to report a policy trained on wrong labels as
losing.

JUDGEMENT: stage4_check — Claude, 2026-10-26: overfit to 0.95 after U 300 updates, a 2-launch
closed loop with a deranged control; versus overfitting alone (competes with checkpoint-rl.md
`verification_plan`). Whether the first method counts as working rests on this.

Stage 4 pass rule: the overfit check, the closed-loop check and its negative control pass;
`rl recount` reproduces every number, including the argmax line texts. A passing stage 4
supports this claim only: the first method, the scorer and the execution path together move
this model to the audited winning action on one real rung, and that action wins when
executed; it says nothing about tactics, other rungs or transfer.

### Stage 5: the one-decision ladder (the reverse curriculum)

With the same method and checks, step earlier along the training root's ladder: audit the
next earlier rung (about seven launches with its reference), add it to the training task set,
train from the current adapter for `U` updates, evaluate, and run `rl confirm` on it (one
launch). Pass rule per rung: its audit passes the stage 2 rule, the curriculum rule passes
after `U` updates, and `rl confirm` passes (a) to (d); the deranged control is not repeated.
Reported beside it, not part of the rule: whether every earlier rung's argmax still wins in
`rl evaluate` (forgetting). A rung that does not pass ends the run; a flat rung is skipped by
the declared skip rule and reported; each new rung's evaluation orderings are drawn when its
task is built, so earlier training never saw them. A held-out root, if the owner wants one,
is a source run plus about seven launches per rung, audited and evaluated only at the end
with `rl evaluate`.

## Verification

Principles: the oracle is independent of the code under test (a hand calculation, a slow
reference, a real log, a rendered string, or the stated contract); every important check
names a negative control that must fail; game-boundary fixtures are synthetic until stage 1's
logs exist and then sliced from them into `tests/twwarhammer3/checkpoint_rl/`; a passing
component test establishes a contract, not a live effect. A proposed live check is put to the
owner before it runs; a pass before agreement is evidence, not verification. Run
`uv run --locked pytest -ra <tests> --basetemp=runs/test-scratch/<name>` and
`uv run --locked ruff check .`; numerical tests use `--extra llm` and are reported as
unavailable, not passed, when it is absent (the default venv has no torch).

How the checks build on each other, and what each rules out:

| Level | Check | Rules out |
|---|---|---|
| The math | numerical and `exact_table@1` oracle tests (stage 3) | wrong gradients, masking, temperature, sign and zero-signal bugs |
| The method moves the policy where the reward points | method-agnostic tests with the mapping control (stage 3), overfit check (stage 4) | an optimizer or update that does not follow the objective; a slot-to-candidate mapping error in the method |
| The policy reads the state | synthetic check, its generator tests and its shuffled control (stage 3) | memorising an index or a single answer; a rendering that hides the needed fact; a label leaking through another field or a split shift |
| What was learned wins in the game | closed-loop check (stage 4 with its deranged control, each new rung in stage 5 without it) | a slot-to-candidate bug shared across the code (by the rendered line text), an id-to-batch mismatch, a table built wrong, an execution or reload fault |
| It generalises | held-out rungs and roots (stage 5 and later) | nothing with certainty; this level is statistics with error bars |

The handoff's [test table](checkpoint-rl.md#proposed-unit-and-component-tests) stands for
the numerical core (scores and gradients against a token-by-token reference, limits, the
categorical policy, same policy throughout, artifact integrity, split leakage), with two
changes for `exact_table@1`: behaviour association means that before each update the adapter
hash equals the previous update's after-hash and each task's mapping hash equals
`candidates(context)` rebuilt; and the lifecycle row's duplicate-consumption rejection does
not apply, since decision 5 reuses a table across updates, each use recording its ordinal.
Rows below are what this design adds or changes.

| Check | Oracle and negative control |
|---|---|
| Watcher and statuses | Streams: the real `restore-a` `native.jsonl` cut before `restored`; a copy with the name or tick changed; a copy with an `error` row at tick 1150 whose observation stream continues past the checkpoint time; a copy with an `error` row after the injection tick; an `error` row at the injection tick with no `lua` event, in the real row shape (`Error: Lua <label>: ...`, copied from `runs/twwarhammer3/checkpoint-siege-20261025/siege-equip-06/native/native.jsonl`) with the label `inject`, and a `SyntaxError` variant; a `detached` row before the end; a `frida_error` row (no tick) after `done`; the full stream (`done`, then `tick` 2001, then the normal detach); the same with a synthetic won result observation before `done`. Expected: `restore_failure` ×3, `restore_fault`, `injection_failed` ×2, `restore_fault`, `stopped` with `late_fault`, `stopped` with no `late_fault`, `won` with no `late_fault`; no reward except the last. Negative controls: a watcher that reads only observation fields returns an engine status on the third fixture; a rule matching the prefix `Lua inject:` classes the injection-tick rows as `restore_fault`. |
| Agent fault path | In the existing Node harness, with a fake `ENV.checksums` entry and `restore.data`: a mismatching checksum sends `error` matching /differs from the checkpoint/ and no `restored`, and later `session_step` and `post_tick` calls send nothing; positive control: a matching checksum sends a `tick` row and no error. |
| Injection in Lua | Under lupa with controlled `battle_time` and a test-defined `state`: a valid message becomes `state.pending` and `apply_pending` acknowledges it with the given request id and `based_on`; each refusal returns `accepted: false` with its reason, raises nothing and leaves pending unchanged; the export is absent until `load()` ran with an enabled session. |
| Grid rule | From a hand-written start time, `G` 300 and a list of logged observation times, the check accepts on-grid observations and flags an off-grid one, ignoring `Loading` and the result; a no-acknowledgement stream spaced 1,200 ms still yields `G` 300 (the oracle is `tick_ms` rounded up to the 100 ms engine tick, with the start from `mod.log`, not the spacing); a `T` with `100T` on the grid and a `T` whose context precedes `100S` are refused; the context time and expected `applied_ms` for `T = S + 2` match a hand computation (`100S + 100`, `100S + 400`). |
| Attribution | One fixture per clause that fails only that clause: context hash different (`injection_failed`); context missing from the log with a seq gap there (`infrastructure`, a reader miss); `accepted: false`; request id differs; results count differs from the batch length; one result not ok (reason `refused`); `applied_ms` differs from the expected grid time or between repeats; `applied_ms` equal to the result observation's `time_ms`; divergence before `applied_ms`; witness missing. Plus one that passes as `no_effect` and one that passes with `witness: unchanged`. Negative control: a predicate of request id plus all-ok accepts the "results count differs" fixture. |
| Reward extraction | From `attempt.json` shapes: won; won with a `late_fault`; timer win; `stopped`; `restore_fault`; `injection_failed`; `no_effect` won. Reward from `engine_ending` only, status and `late_fault` separately. Negative control: an extractor that reads `late_fault` or `manifest.error` instead of `engine_ending` fails the second case. |
| Candidates | Purity: same context, same list and hash; sentinels in `evaluation`, `final`, `setup`, the dropped fields, unseen enemies' state and record metadata change nothing; a public change changes the list; every batch passes `validate_orders`; a fall-back point is inside `terrain.bounds`; no two batches equal and the dropped duplicate is recorded; `noop` present; hand-written (id, description, batch) triples match on an ordinary context and on one with `f2` routing (where `rush_nearest` equals `charge_f1` and the later one is dropped); `attack_nearest` and `rush_nearest` get different descriptions, and a list with two equal descriptions is refused. `slot_to_candidate` under (1,2,3,4,0) maps every slot to the candidate whose line the rendering prints there; negative control: an implementation using `p.index(k)` fails. Evaluation orderings: `K_eval` distinct per task, 3 for a three-candidate list, never drawn by training. |
| Public projection | `public()` is what `_drive` uses and `context_projection` builds on; a sentinel in each stripped key never reaches the rendered context; `setup` present in a restore's observations is stripped; two views of one state from different launches (different `job`, `battle` and `seq`, one with `orders`, `dest` and ability `last_issued_ms`, one without) hash alike under the projection and differ without it; a change in `enemy_roster` changes the hash. |
| Library and launch refusals | A flipped byte in the replay copy is refused before launch; a record whose exe, pack or agent hash differs from the environment is refused before `RuntimeLock`, and one that matches proceeds to a faked launch; an unusable record is refused; the limits check refuses a plan whose caps cannot contain `remaining_ms` plus overhead and accepts one that can; a save name present among the bystanders is refused before `only_replay`; a missing Frida venv is refused before launch; the copy is removed, saved replays moved out and the bystanders returned after an exception and after an interrupt, with `only_replay` unchanged. |
| End rule | A source stream with saves declared past its result observation ends at the result after the earlier `saved` rows arrive and records the later saves as not reached. |
| Comparator | Two identical synthetic attempts pass; one differing tick, observation hash, reading or ending fails; rows after the earlier engine-ending tick are reported as uncompared; a reading present on one side only is reported, never dropped; the recount of `checkpoint-check-20261025c` still gives 2,001 ticks and 699 mismatches for `changed` and passes. |
| Tasks and task sets | A task built from an audit table carries the table's rewards, descriptions and mapping hash exactly; a refused candidate is absent from the task; the same declaration builds the same task set hash; a label transform changes only training-split rewards, is recorded in provenance and changes the hash; a held-out task is never transformed; a real set with one family in two splits is refused, a synthetic set split by job passes; the synthetic generator tests of stage 3. |
| Run records | Every update record lists its batch's task hashes; recount refuses a run whose records include a held-out task hash; `fresh` saves `adapter-0000/` before the first update; adapters exist only at the start and the end. |
| Evaluation and comparison | Fed slot-indexed scores from a fake scorer biased to one slot, under the two cycles, every metric of decision 8 equals a hand value computed independently; a second evaluation of the same adapter on the same task set is refused; a start adapter's evaluation records 0 updates and no training set; `rl compare` refuses two evaluations that differ in any field of its refusal list, naming the field, and accepts two that match. |
| Closed loop | On synthetic records: each pre-launch check and each of clauses (a) to (d) fails on a fixture that breaks only it (a declaration whose tensor hash differs; scores off by more than the tolerance; a chosen id different from the evaluation's; an evaluation file without an overfit pass; a chosen id whose true reward is 0; a mapping that returns a neighbouring candidate's batch; an argmax line text that differs from `describe` of its mapped candidate; an attempt that differs from the audit attempt at one tick; a table whose reward differs from its attempt's ending; a live ending that is a loss), and all pass on a clean fixture, including one with two winners whose orderings' argmaxes differ. |
| Exclusion | Two real subprocesses on one real lock file: holder alive, the other phase refuses; holder killed, the lease is free, the next phase starts and the killed phase's record is not marked complete. The game-process check uses a fake `running_pids`; `rl confirm` refuses to launch while its own model process is alive. |
| Recount | Re-derives every reported number of a source run, an audit, a task set, a training run, an evaluation and a confirm from the records alone; a changed record changes the verdict; the verdict carries the checker's hash and the input hashes. |

## Exposing checkpoint errors

Statuses form one closed set: `won`, `lost`, `draw` (engine results); `stopped` (a declared
`stop_tick` reached, no ending); `restore_failure` (no `restored` with the expected name and
tick, or a fault before it); `restore_fault` (a fault after the handover and before the end,
or a handover reading unequal to the source's reading at the save tick); `injection_failed`
(an attribution clause failed, the reason included: `refused` for an engine refusal, the
agent's message for a broken export); `infrastructure` (a launch failure before `restoring`,
a reader miss, a timeout, the game gone, a refused launch); `interrupted`. Only the first
three carry a reward. `late_fault`, `no_effect` and `witness: unchanged` are flags beside a
status, never statuses. Every detector writes its reason into `attempt.json`; an unexplained
detection is a bug to report, not a tolerance to add.

| Detector | Where | Status or action |
|---|---|---|
| Replay copy hash differs from the record; exe, pack or agent hash differs; record unusable; `T` on the grid or with a context before the handover; save name taken; leftover `checkpoint-aside/` or work directory; missing Frida venv | before launch | refused, no launch; a game update means the agent's offsets must be re-derived and the Land check re-passed, and library entries are build-bound |
| No `restored` with the expected name and tick; `error`, `frida_error` or an unexpected `detached` | watcher | `restore_failure` before the handover, `restore_fault` after, `injection_failed` for an `error` at the injection tick with no `lua` event before it, `late_fault` after the end |
| Handover reading differs from the source's reading at the save tick (private readings of both sides, never policy input) | at handover | `restore_fault` |
| Context observation missing (a seq gap) | attribution | `infrastructure` (a reader miss) |
| Context hash differs; `accepted: false`; acknowledgement, `applied_ms`, divergence-before-apply or witness clause failed; unit ids or roster differ from the context | attribution | `injection_failed` |
| Identical attempts differ in a checksum, observation hash or ending after the handover | comparator, on every repeat and in `rl confirm` | the rung is blocked until explained |
| Replay copy hash changed after a run | after the run | the library entry is marked suspect; later restores from it are refused |

Re-execution: an attempt ending `infrastructure` or `interrupted` may be re-executed once, by
a new plan naming the failed attempt, with the same batch; `restore_failure` and
`restore_fault` are never re-executed and block the rung until explained. Per-candidate
counts of every status are part of each audit and confirm report, so a fault that correlates
with an action is visible.

## Records, resuming and the first report

`attempt.json`, written once and never edited: the library record (and its root); the plan
(ticks, `δ`, limits, `observe_ms`, `source_control`, `CANDIDATES_VERSION`, the reading Lua
hash); `source_revision`, pack, agent and exe hashes; the context's `time_ms`, projected hash
and observation; the candidate list and mapping hash; the injected message and its hash; the
`lua` event, the acknowledgement, `applied_ms`, the first divergent tick and the witness
observation; `engine_ending`, status, reason and flags; restore evidence (`restored` tick,
checksum count after handover, handover reading equality, seq gaps); wall times per phase and
the memory snapshot. Update records carry what the data-flow table lists, plus the method and
version, its config hash, the base revision, tokenizer and template hashes, rendering and
candidates versions, token counts and temperature.

The declaration a model phase reads: base id, revision, directory and file hashes; adapter
directory and file hashes; tokenizer and template hashes; `rendering_version`,
`candidates_version`, `token_cap`, `eos_token_id`, `temperature`, `adapter_seed`.

Resuming: a new plan names the earlier plan and the attempt hashes it reuses; an audit is
complete when every (candidate, repeat) and the reference have complete records from a named
plan; `rl` commands stop at the first failure and never retry on their own. On an interrupt
the replay copy and any saved replays leave the game's folder and the bystanders return; the
manifest records `interrupted` and the cleanup done; a leftover work directory or `STOP` file
is reported and cleaned by hand before the next launch.

The first report (at most 20 lines, in the log, its lines printed by `rl recount`): the
synthetic check's held-out accuracy (minimum over evaluation orderings) and its control
beside the majority-class, index-0 and start-adapter baselines; then per rung, root, tick,
candidates `n`, winners `k`, refused candidates, mass before and after with spread over the
evaluation orderings, `k/n`, the index-0 baseline, KL from the start adapter, the
pre-launch checks and four closed-loop clauses and the deranged control, launches used,
status counts per candidate, source revision and adapter hashes; one sentence that this is
fitting on one rung, not tactics or transfer; links to the records and the recount verdict.

## Resources and lifecycle

- Serial only: a game phase refuses while the GPU lease is held or a CUDA process exists; a
  model phase refuses while a game process exists. Each phase records Windows free memory
  and WSL `MemAvailable` at its start.
- Limits are plan fields recorded in the manifest and refused when they cannot contain the
  rung's `remaining_ms` plus the measured overhead and a margin.
- All phases call `committed_revision` with the play scope; adapters, records and evidence
  live under `runs/`. Draft in a worktree; never edit the scope while a collection runs.
- A Steam build change stops everything with a report; the agent is build-specific and is
  not re-pinned by an agent.
- Game time only in owner windows; the checks name their launch counts first. No API spend.
- Expected cost: 52 s plus the battle after the handover per attempt; the Land source's
  ending time is unknown until stage 1's first launch; its engine deadline is about 1,205 s.
  Stages 1, 2 and 4 together need about 19 launches; stage 3 needs GPU time only (two
  300-update runs plus tests); stage 5 needs about eight launches per rung.

## Owner decisions

Before stage 1: decisions 1, 2 and 4 and decision 7's source control; the rung selection and
witness values below; a game window for eleven launches with source limits of about 1,400 s;
whether `check_wh3_restored_episode.py` (marker `stage1_check`) is agreed as a verification
method before it runs; whether to re-run the siege and team checks after the mod change.

Before stage 2: decision 3; the training root (the Land scenario is proposed;
`ksl-raiders-emp-halberds` is the candidate second root); repeats; whether a tick search is
allowed. The first rung is the late rung (decision 7).

Before stage 3: decisions 5, 6 and 8 (decisions 2 and 3 are already answered, since stage 3
uses their code); the training settings below; whether the synthetic check (marker
`synthetic_check`) is agreed as a verification method.

Before stage 4: `θ_fit` and `U`, and whether the overfit and closed-loop checks (marker
`stage4_check`) are agreed as a verification method.

Before stage 5: `θ` (`curriculum_rule`); the flat-rung skip rule; a launch budget for the
ladder (about eight launches per rung); whether a held-out root is audited and which
scenario.

Plan parameters, proposed values the owner can accept or change in one line. `observe_ms`
300 and `δ` 2 belong to `dispatch`, `fall_back_m` to `candidate_set`, `ending_margin_ms` to
`ending_margin`, `θ` to `curriculum_rule`, `θ_fit` and `U` to `stage4_check`, `K_eval` to
`method_comparison`, and the synthetic task's values to `synthetic_check`.

JUDGEMENT: rung_selection — Claude, 2026-10-25: readings every 100 ticks, saves every 300 ticks
from 600, late rung 60 s before the ending; versus other spacings. Which states are rungs
rests on this.

JUDGEMENT: witness — Claude, 2026-10-26: 5 s window, dest within 1 m, an already-shown value
or no divergence accepted (flagged); versus requiring fresh evidence or failing such attempts.
Which injections count as executed, and so carry a reward, rests on this.

JUDGEMENT: training_settings — Claude, 2026-10-26: K 4 fresh permutations per update, temperature
1.0, LoRA r 8/16/dropout 0, AdamW lr 1e-4, no weight decay, token cap 1,536, batch 16; versus
other values or SGD. Stage 3 and 4 results rest on this.

The LoRA shape above is the SFT smoke test's (attention and MLP projections); AdamW uses
PyTorch's default betas (0.9, 0.999). Spire's RL used AdamW with weight decay 0.01; decay is
dropped here because it moves weights without a reward signal.

## Later methods (not planned here)

The owner asked on 2026-10-26 to plan only the first method ("don't worry about planning the
other methods now"). Each later method enters through `METHODS`, runs the method-agnostic
tests (restated in expectation if it samples), trains on task sets and is compared through
`rl evaluate` and `rl compare`. Candidates, in rough order of difficulty: a sampled policy
gradient on the same one-decision tables (REINFORCE with a leave-one-out baseline, which
shows what sampling costs against the exact expectation); multi-decision episodes as chains
of restores, with RLOO or GRPO-style group baselines; free-form order generation scored by
the engine (the usual RLVR setting); a live local controller in the benchmark harness. What
the reviews already established for chains, to carry into their plan: a chain step needs a
descendant-restore check that has never run in this repository; with the default spacing
(rests on JUDGEMENT checkpoint-rl-plan.md `rung_selection`) the late rung leaves 60–90 s of
battle, too little for a second decision, so chains need an earlier rung; a chain step has
no no-injection reference, so its attribution rests on the acknowledgement and witness alone.
The chain design and its markers `episode_form`, `descendant_check` and `chain_settings`, all
this plan's own undecided proposals that were never committed, were removed with that
direction.

## Risks the plan does not remove

- A one-decision rung measures fitting on one checkpoint of one root; transfer needs several
  roots and held-out ones, and the first results will not show it.
- The 0.6B model may fail the synthetic check; that stops the plan before game data is spent,
  and changing the model, rendering or settings is a declared change.
- The model may fit the training orderings but not read candidate lines, so the overfit
  check fails under the evaluation orderings; the records classify that as a finding about
  the model or rendering, not a reason to evaluate on training orderings.
- The hold source may lose, or every candidate may win or lose at the late rung; both are
  findings that change the rung or the root, reported whole.
- The synthetic rule is far easier than battle tactics; passing it only shows the stack can
  learn from rewards.
- Restores rebuild `enemy_roster` from observations made while Lua readings lag; stage 1
  checks that restores agree on it, and a disagreement would block the projection as
  designed.
- A game update ends the whole track until the agent's offsets are re-derived and the Land
  check re-passed.
