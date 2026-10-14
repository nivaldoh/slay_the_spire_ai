"""Remotely trained open-weight models (planned, skeleton only): game-reward RL with GRPO
on Tinker, an ECHO-style dynamics-prediction arm, and baselines on the same tasks.

Stages of docs/spire/open-weight/README.md, by module:

- A, environment: ``tasks`` (curriculum stages, seed splits) and ``env`` (real game and
  simulator behind one step interface).
- B, starting point: ``policy`` (a remote model over a Decision's choices) and ``evaluate``.
- C, game-outcome RL: ``rewards``, ``rollout`` and ``grpo``.
- D, dynamics learning: ``dynamics`` (observable consequences as targets) and the ECHO term
  in ``grpo``.
- E, scale: the same modules on GLM-5.3. ``remote`` holds the Tinker transport and prices.
"""
