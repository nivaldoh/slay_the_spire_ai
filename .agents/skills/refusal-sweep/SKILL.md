---
name: refusal-sweep
description: Remove each refusal (a Python raise or a Lua error()) in one source file, one at a time, rerun the tests, and list the removals no test catches. Use before an agreed check or a guarded module changes, after a model upgrade, or to find test gaps (docs/workflow.md, checks of checks). Offline; never launches a game.
---

# Refusal sweep

The tool is `scripts/refusal_sweep.py` (its docstring has the arguments). It plants in a scratch
checkout, never the main tree, and runs every version without bytecode.

1. Card first (docs/workflow.md): which file, which tests, what "caught" means.
2. `git worktree add --detach runs/<task>/scratch main` (never under /tmp, never a symlinked
   .venv). Copy any uncommitted test file you want scored into the scratch tree.
3. Near a launch, stub its first step in the tests before planting (WH3 checkpoint: the
   RuntimeLock; Spire: `communication_config`), and afterwards check the Windows-side files'
   modification times (`C:/wh3-agent`, `C:/spire-agent`, CommunicationMod's config).
4. Run one sweep at a time, and nothing heavy beside it: timing tests flake under load and a
   flake reads as "caught". Python:
   `uv run --locked python -I scripts/refusal_sweep.py runs/<task>/scratch src/x.py x x tests/<dirs>`;
   Lua: pattern `'(?<![\w.:])error\('`, replacement `'tostring('`. Pass test folders in
   alphabetical order (a WH3 stats test reorders a price table the Spire CLI test reads).
5. For each MISSED line, write a test that fails on that removal for the stated reason
   (a refusal, not a KeyError further on), as a pure addition. Rerun the sweep after.
6. Count a miss "equivalent" only after showing another assertion rejects the same behaviour.
   Record before and after files under `runs/<task>/`, then have one reviewer rerun every
   count and plant other wrong versions before the numbers reach the owner.
7. `git worktree remove --force runs/<task>/scratch` when done.

A test written for a planted miss shows that gap closed, not general strength: on 2026-10-29
each later review round still found wrong versions the newest tests passed.
