# Original-engine starter mechanics evidence

The [captured fixture](../tests/fixtures/engine_starter_transitions.json) contains
12 transitions from three completed original-engine combats on 2026-10-11:
`runs/first-random-v2-20261011/episode-0000` and
`runs/heuristic-replay-20261011/episode-0000`, plus
`runs/loss-restart-probe-20261011/episode-0000`. All are Ironclad, Ascension 0,
with unupgraded starter cards and the same `FuzzyLouseNormal` /
`FuzzyLouseDefensive` encounter. They are examples from one encounter, not
independent coverage of different encounter distributions.

The fixture records engine/mod hashes, each episode's implementation revision,
full trace SHA-256, original JSONL line numbers, action command, selected card
and target indices, and minimal public fields before/after the action. Every
retained gameplay value was copied from those exact observations. The action's
next stable response is linked by its recorded action ID in the source trace.
The committed projection excludes seeds, UUIDs, ordered piles, private enemy
move fields, and reflected private power state. It contains no game assets or
decompiled source and is under 50 KB.

## Observed coverage

| Fixture case | Engine observation preserved and checked |
| --- | --- |
| `strike_triggers_curl_up` | Strike spends 1 energy; target HP 14 → 8; Curl Up 7 disappears and target block becomes 7. |
| `defend_adds_block` | Defend spends 1 energy; player block 0 → 5; health and enemies are unchanged. |
| `bash_adds_vulnerable` | Bash spends 2 energy; target HP 14 → 6; Vulnerable 2 appears; Curl Up 4 becomes block 4. |
| `vulnerable_strike_through_block` | Strike spends 1 energy against Vulnerable 2; block 4 → 0 and HP 6 → 1 account for 9 damage. |
| `target_one_after_target_zero_died` | Dead target 0 stays in the monster array; `play 3 1` hits the living target 1. The adapter retains index 1 and excludes index 0 from targeted candidates. |
| `partial_block_end_turn` | A visible 7-damage attack meets 5 block: HP 73 → 71; block clears, energy refreshes to 3, and the turn advances. |
| `full_block_end_turn` | The same visible attack meets 10 block: HP stays 78; unused block clears and energy refreshes to 3. |
| `strength_and_vulnerable_tick` | The first Louse buffs to Strength 3; its next displayed attack is 8; Vulnerable decreases 2 → 1 and its previous block clears. |
| `weak_strike` | With Weak 2, an unblocked Strike changes target HP 8 → 4. |
| `victory_heals_six` | The engine reports the same monster room `COMPLETE`; Burning Blood is present and HP changes 64 → 70. |
| `victory_heal_capped` | A second engine terminal observation changes HP 78 → maximum 80 with Burning Blood present. |
| `end_turn_engine_death` | END changes HP 1 → 0 and produces `GAME_OVER` / `DEATH` with `victory=false`, even though `room_phase` remains `COMBAT`. |

The [regressions](../tests/test_engine_regressions.py) feed these captured states
through the adapter. They check observed commands against its legal candidates,
card/target identity, public damage/block/power values, ordinary energy costs,
stale-action rejection, zero-energy action masks, and terminal recognition.
They do not implement a simulator or rerun the game on each pytest invocation.
The numeric checks protect the interpretation of captured engine observations;
they do not establish general formulas for unseen mechanics.

## Verification

Run the fixture regressions from the repository:

```bash
uv run pytest tests/test_engine_regressions.py
```

When the ignored original runs are present, three additional provenance checks
verify the complete trace hashes, implementation revisions, line references,
action linkage, and every projected field against the source observations.
Those three checks skip in a fresh checkout without local evidence. To verify
against artifacts in another checkout:

```bash
SPIRE_EVIDENCE_ROOT=/path/to/slay_the_spire_ai uv run pytest tests/test_engine_regressions.py
```

Validation after adding the loss capture: **29 tests passed**, including all three source-trace
checks. Ruff passed for the regression module.

The loss probe completed two consecutive end-turn-only episodes, each ending
in an engine-reported death at zero HP. Both recorded the same settled
combat-start fingerprint,
`177b2fcdc80ed0e9efb7d2a01191a40df6e40d4123867d09e091fa122edc12c4`,
after choosing the 100-gold Neow option. The second episode demonstrates a
seeded restart after a genuine gameplay loss. Its recorded profile snapshot
still shows Ironclad unlock progress 817, matching the first episode's snapshot;
the terminal screen's score is 5. Do not infer unlock-progress changes from the
displayed score alone. This verifies the observed two-episode case, not every
profile or unlock boundary.

## Limits and observed caveat

The first combat-ready observation labels both enemy intents `DEBUG`. After the
first card, the bridge reports `BUFF` and `ATTACK`. The fixture retains the
unknown intent without substituting private damage values. This is a real
initial-state visibility/timing limitation; these tests do not certify that
every command-ready observation already contains the intent visible on screen.

The captured death supplements the synthetic terminal contract tests; other
game-over screen variants remain outside this evidence. Victory responses omit
combat state, so this artifact does not assert the final card's post-play energy, precise
overkill damage, or enemy death animation state. Burning Blood attribution is
supported by the relic and health observations in this narrow setup, not by a
separate callback from the engine.

These captures do not cover upgraded/nonstarter cards, potions, card-selection
screens, bosses, other encounter mechanics, player Strength, multi-hit damage,
draw-order privacy, or hidden-state independence. A future simulator needs its
own differential comparison against the engine; passing these adapter tests is
not simulator fidelity evidence. Re-capture and review this evidence when the
engine, mods, observation contract, or benchmark mechanics change.
