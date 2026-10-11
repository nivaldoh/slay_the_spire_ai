# Initial neural learning core

This is a small, randomly initialized CPU actor-critic for the public
`ironclad-starter-combat-v1` decision contract. It is infrastructure for an
original-engine learning experiment; unit tests do not demonstrate learned game
performance. Install the locked optional dependency with
`uv sync --locked --extra train`, then run
`uv run --extra train pytest tests/test_learning.py`.

The encoder (`starter-set-scorer-v1`) applies a shared 16-unit card encoder to each
card, sums separately over hand/draw/discard/exhaust piles, and sums a shared
16-unit enemy encoder over enemies. A 64-unit context feeds a critic and a shared
candidate scorer. The scorer combines that context with the candidate's card,
target, and play/end indicator. Indices select the appropriate object but never
become numeric model features. Duplicate card/target instances remain separate
legal candidates. Reordering cards/enemies permutes their action scores while
preserving the value estimate, up to floating-point summation error. Padding in
training batches receives negative-infinity logits and zero action probability.

Features are fixed scaled public health, block, energy, turn/counters, card type,
cost/upgrades/flags, visible intent and damage, and public power amounts. Named
power channels cover Strength, Dexterity, Weak (engine ID `Weakened`), Vulnerable,
Frail, Curl Up, Ritual,
Artifact, Metallicize, and Barricade; unknown powers share amount/count channels.
Unknown card IDs share a channel, but action legality remains restricted by the
protocol adapter. The model omits names, UUIDs, slot positions, seed, private RNG,
unrevealed order, gold, potions, and relic identity. This is a deliberate initial
starter-combat representation, not a general deck/relic encoder.

`NeuralPolicy.choose(Decision)` returns the exact `Action` object. Immediately
call `choice_metadata(decision.id)` to log the candidate order, selected index,
behavior version, model SHA-256, encoder/observation versions, old log probability,
old value, and evaluation mode. Seeded stochastic sampling has its own CPU RNG;
deterministic evaluation takes the first maximum and does not advance that RNG.
Frozen stochastic evaluation calls `reset_sampling(suite_seed)` for each episode
so its samples are independent of the restored training RNG history.
The runner must record this metadata before executing the action. Reconstruct
already-audited public decisions with `decision_from_dict`; this helper is not a
replacement for auditing raw bridge messages or execution outcomes.

`Transition` retains that decision, selected action ID, old log probability/value,
reward, terminal flag, behavior version, ordered candidate IDs, and model SHA.
`PPOTrainer.update` accepts complete episodes only and checks every action,
candidate mapping, model identity, and recomputed behavior probability/value
before any update. The collector must reject deterministic evaluation samples,
prefix actions, interrupted/unsupported episodes, and unconfirmed executions.
Old batches cannot be reused after the model changes. Truncations require a
separate future bootstrap contract; they are not treated as losses here.

Reward version `combat-terminal-health-v1` uses zero intermediate rewards,
`1 + 0.25 * ending_hp / max_hp` for a verified win, and `-1` for a verified loss.
Ending health is the engine's terminal health, including Burning Blood healing.
Wins and health must also be reported independently of training return.

PPO defaults are undiscounted return (`gamma=1`), GAE lambda 0.95, four epochs,
minibatches of 32, Adam learning rate 0.0003/epsilon 0.00001, policy clip 0.2,
entropy coefficient 0.01, value coefficient 0.5, gradient norm limit 0.5, and
approximate-KL early stopping at 0.02. Advantages are normalized over the batch
using population variance. The critic uses unclipped squared-error loss. The
implementation follows the algorithmic ideas illustrated in
[CleanRL PPO at fe8d8a0](https://github.com/vwxyzjn/cleanrl/blob/fe8d8a03c41a7ef5b523e2e354bd01c363e786bb/cleanrl/ppo.py)
with new code specialized to variable candidate sets and complete episodes;
CleanRL is not a runtime dependency.

The runner exposes `train --learning-rate VALUE` for a declared optimizer-rate
experiment; omission keeps 0.0003. It records the resolved rate in the run
configuration, learner checkpoint and Adam parameter groups. Resume preserves
that rate and rejects overrides. Older checkpoints that omit the runner field
retain their original 0.0003 default. Changing this option alone does not establish
better learning; compare the final artifact under a fixed evaluation contract.

`PPOTrainer.state_dict()` returns an independent snapshot containing model,
optimizer, policy sampling RNG, minibatch RNG, CPU torch RNG, update counter,
configuration, and version contracts. `load_state_dict` restores these and
rejects version/configuration mismatches. The dictionary supports
`torch.save`/`torch.load(weights_only=True)`. Saving optimizer state follows
[PyTorch's checkpoint guidance](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html).
The caller remains responsible for atomic checkpoint files, manifests, run
budgets, consumed/pending episode identities, external RNGs, and trace hashes.
Save before/after a whole optimizer update; if it fails partway through, restore
the pre-update checkpoint rather than keeping a partially updated model. A live
game cannot be resumed from this checkpoint.

Regression checks cover permutation behavior, duplicate identities, padding,
finite one-action/one-transition cases, changed weights, rejected stale/corrupt
behavior data, checkpoint sampling reproducibility, and identical subsequent
Adam updates after restore. Initial same-seed combat learning remains a
learnability diagnostic, not evidence of generalization.
