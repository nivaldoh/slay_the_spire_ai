# Original-engine inventory mechanics evidence

The [inventory fixture](../tests/fixtures/engine_inventory_transitions.json)
captures 16 transitions from six completed original-engine episodes in
`runs/starter-inventory-20261011`. These extend the earlier
[starter mechanics evidence](mechanics.md) with Cultist, Jaw Worm, and two
same-species Louse compositions. All fights use Ironclad, Ascension 0, and the
unupgraded starter deck. These are observations from particular fights, not
general formulas or a simulator fidelity result.

The inventory completed its conditional schedule on 2026-10-11 with 18 attempts
and `admissions_valid=true`. Its final `inventory.json` SHA-256 is
`b2bd3789be73be6c33d85108c8cd63bf9dcf8aff4fb8257742e0e83a3a30d12c`.
The frozen contract SHA-256 is
`72d14fc6f5bbe7765479572806431f142260dc553d2da5d7bdc648976a43f972`.
This fixture preserves that inventory identity; admission decisions remain in
the original inventory record.

## Sources and scope

All attempt paths below are beneath `runs/starter-inventory-20261011/runs/`.
The fixture stores their full trace, manifest and source-patch hashes, exact
source status, implementation revision, protocol source hash, public start
fingerprint, and original line numbers for each observation, decision, action
and acknowledgement.

| Attempts | Public start and role | Evidence used |
| --- | --- | --- |
| `attempt-0007`, repeat `attempt-0013` | Cultist, 80/80 HP, 199 gold; admitted scenario `spireinv07` | Ritual, Strength, displayed attack and blocked turns; the complete 24-action heuristic replay matches. |
| `attempt-0009`, repeat `attempt-0014` | Jaw Worm, 80/80 HP, 199 gold; admitted scenario `spireinv09` | Mixed intents, block, Strength and displayed damage; the complete 27-action heuristic replay matches. |
| `attempt-0015`, `attempt-0016` | End-turn probes at the respective admitted starts | Unblocked damage and actual engine `DEATH` for Cultist and Jaw Worm. |
| `attempt-0005` | Two `FuzzyLouseNormal`, 88/88 HP, 99 gold | Distinct Curl Up amounts, Strength, and original target-slot identity after the first Louse dies. |
| `attempt-0011` | Two `FuzzyLouseDefensive`, 88/88 HP, 99 gold | Independent intents, Weak, reduced Strike damage and target-slot identity. |

Both same-species Louse starts chose the max-HP Neow variant. They failed the
inventory's 80-HP admission condition and remain explicitly outside the catalog.
Their complete fights still provide mechanics observations. No new Louse
scenario was admitted, and the inventory scheduled no Louse repeat or death
probe. The earlier mixed-Louse evidence remains separately documented.

The recorded implementation revision is
`cbe09ed9a361c8c7df447bc08ec1fe61a5540cd8`. Child manifests record documentation
changes during collection (`docs/state.md` and, in later children, an untracked
results document); the fixture preserves these statuses and each saved patch
hash rather than describing the whole checkout as clean. The inventory freezes
implementation source fingerprints and game/mod hashes. The fixture retains
those engine pins and the protocol source SHA-256
`3f6caab2c80d8e75e762bb408ba0a21e3a97d26f8331a377f9fd13fa091f40bc`.

## Numeric observations protected by regressions

| Mechanic | Captured observation |
| --- | --- |
| Cultist opening | Its `BUFF` turn produces Ritual 3, Strength remains absent, and its next displayed attack is 6. |
| Cultist later turns | Strength changes 0 → 3 and then 3 → 6; next displayed attacks change 6 → 9 → 12. Ten player block absorbs the captured attacks, then clears. |
| Cultist unblocked attack and death | A displayed 6 attack changes player HP 80 → 74. Later, Strength 15 and a displayed 21 attack precede HP 20 → 0 and `GAME_OVER` / `DEATH`, `victory=false`. |
| Jaw Worm attack/defend | A displayed 7 attack adds 5 monster block. It is fully blocked in the heuristic fight; the unblocked probe loses HP 69 → 62. |
| Jaw Worm defend/buff | Captured buffs add block 0 → 6 and Strength 0 → 3, then 3 → 6. The next displayed intents are `ATTACK_DEFEND` 10 and `ATTACK` 17. |
| Jaw Worm block and death | A displayed 17 attack meets 15 player block and changes HP 79 → 77. The death probe reaches Strength 9, `ATTACK_DEFEND` 16, then HP 5 → 0 with the actual `DEATH` screen. |
| Two Normal Louses | Curl Up amounts are independently 4 and 7. A Strike changes target 0 HP 10 → 4 and adds its 4 block without changing target 1. After target 0 dies, `play 2 1` still hits the original target 1. |
| Normal Louse later buff | The surviving Louse's Strength changes 3 → 6, its old 7 block clears, and its next displayed attack is 13. |
| Two Defensive Louses | Their simultaneous intents are `ATTACK` 6 and `DEBUFF`; player Weak changes 0 → 2 while 10 block prevents health loss. |
| Weak Strike and Curl Up | With Weak 1 and target 0 dead, `play 1 1` changes target 1 HP 15 → 11 and triggers its 3 Curl Up block. |

The tests run the public adapter against these captured states, checking exact
legal command/card/target identity, stale-action rejection, turn and energy
refresh, public numeric values, and engine terminal recognition. The two repeat
checks compare complete action sequences, prefixes, initial public states and
every public transition, including terminal results. They establish equality
for these recorded replays, not hidden-state or arbitrary-profile equivalence.

## Verification and limits

The committed fixture is 91,268 bytes. It contains minimal public observations
and provenance, excluding seeds, UUIDs, draw arrays, private enemy move IDs,
private base damage and reflected private power flags. It includes no assets,
decompiled source or proprietary game files. The source runs remain ignored
local artifacts.

```bash
uv run pytest tests/test_inventory_engine_regressions.py tests/test_engine_regressions.py
```

To check captured values against the original traces in another checkout:

```bash
SPIRE_EVIDENCE_ROOT=/path/to/slay_the_spire_ai uv run pytest tests/test_inventory_engine_regressions.py tests/test_engine_regressions.py
```

Validation with original artifacts available: **73 tests passed**, including
all trace hashes, independent child audits, per-action line linkage, final
inventory linkage and complete admitted-scenario replay checks. These local
provenance checks skip when the ignored original artifacts are absent. The
fixture tests themselves do not launch the game.

This evidence covers the displayed cases only. It does not cover every enemy
move sequence, upgraded or nonstarter cards, potions, player Strength,
multi-hit attacks, other monsters, whole-run behavior, or hidden-state
independence. Burning Blood and Bash/Vulnerable examples remain in the earlier
fixture. Revalidate relevant captures after changing the engine, mods,
observation contract or supported mechanics.
