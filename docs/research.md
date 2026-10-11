# Research contract

## Current question

Can we repeatedly start the same Ironclad Ascension 0 game, enter its first combat,
execute state-bound legal actions, record the engine outcome, and restart automatically?
This is infrastructure validation, not a policy-performance claim.

## Initial scope

- Original Steam engine, fixed Workshop jars, personal profile slot 0 as authorized.
- Seeded `START` and a fixed noncombat prefix. No arbitrary combat reset is claimed.
- A random legal policy followed by an explicit heuristic baseline.
- Raw engine state is diagnostic evidence; policies receive a separate allowlisted view.
- Exclude seeds, RNG state, unrevealed draw order, and private monster state from policies.
- Record terminal gameplay outcomes separately from limits and bridge failures.
- Preserve every attempt and attribute observations/actions to a unique decision state.

No training or final evaluation suite is established yet. Do not interpret debugging seeds
as a held-out benchmark. Milestone B requires a declared start distribution, mechanic
coverage, repeat-reset evidence, measured throughput, and baseline results.
