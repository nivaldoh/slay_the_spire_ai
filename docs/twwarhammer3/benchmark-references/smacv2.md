# SMACv2 tactical coordination reference

[Reference index](../benchmark-references.md). Read this profile for tactical variation,
partial observation and tests of whether a controller actually uses feedback.

SMACv2 evaluates cooperative multi-agent policies in StarCraft II combat. Each friendly
unit is an agent; the enemy is controlled by the game AI. The key similarity to WH3 is
coordinating different units while each has incomplete information. Its action granularity
and stepped clock differ from our high-level, live battle controller.

## How tasks are created

The authors define base maps, unit pools and sampling distributions. Software then builds
new situations at episode reset. This is a designed generator, rather than a separately
hand-authored battle for every attempt. The [paper](https://arxiv.org/abs/2212.07489)
explicitly tests previously unseen settings drawn from the same distribution; that alone
does not establish transfer to new distributions, maps or game rules.

The [distribution code](https://github.com/oxwhirl/smacv2/blob/577ab5a2cff2391f8df582da5731ea9cd6adf3c6/smacv2/env/starcraft2/distributions.py)
samples team composition, positions and other configured capabilities. Weighted team
generation samples an allied roster and copies it for the enemy, extending or truncating
it for unequal team sizes; it can reject all-healer compositions. Position generators
include reflected and surrounded starts. This preserves chosen structure while varying
the concrete problem; it is not arbitrary random placement.

The [wrapper](https://github.com/oxwhirl/smacv2/blob/577ab5a2cff2391f8df582da5731ea9cd6adf3c6/smacv2/env/starcraft2/wrapper.py)
calls each configured generator on reset and passes the combined configuration to the
environment. Several distributions construct their own unseeded `default_rng()` objects:
do not infer that the environment's seed alone reproduces every sampled setup.

## What evaluation measures

The [paper](https://arxiv.org/html/2212.07489v2) finds that timestep-only policies can score
well on some original SMAC tasks. SMACv2 varies starts; its EPO extension masks enemy
observations and removes attack-availability clues that would reveal targets. This
motivates comparing reactive and fixed plans; it does not establish that WH3's current
scenarios require feedback.

The study trained for 10M environment steps, evaluated 20 episodes every 2k steps, and
plotted mean test win rate with standard deviation across three seeds (section 7.1,
Appendix C.3). Hyperparameters were selected using all scenarios; those curves are not an
untouched held-out suite. These are the paper's settings, not a proposed WH3 sample plan.

The inspected [environment](https://github.com/oxwhirl/smacv2/blob/577ab5a2cff2391f8df582da5731ea9cd6adf3c6/smacv2/env/starcraft2/starcraft2.py)
counts completed episodes in `battles_game`, increments `battles_won` for a victory, and
reports `win_rate = battles_won / battles_game`. Episode-limit timeouts increment the
denominator and the timeout count without adding a win. Its `battles_draw` counter aliases
timeouts; this is not WH3's engine-reported draw. Damage and death rewards used for training
are distinct from that win-rate measure. An experiment runner must separately define its
evaluation episodes, training repetitions and uncertainty; environment counters alone do
not provide a complete study protocol.

Agents receive local observations and choose discrete movement, stop and target actions,
with healing actions for the relevant unit type. Global state is available for centralised
training. In WH3, any training or evaluation use of hidden state must stay separate from
the controller's public inputs.

## Timing and failure limits

`step(actions)` sends the joint actions, advances StarCraft by a configured number of game
steps, then returns. The world does not keep advancing for the natural duration of model
inference as it does in WH3. Its win rate therefore cannot answer our API-latency question.

The wrapper retries an invalid reset internally. That mechanism is not a suitable donor
for WH3's rules about preserving failed attempts and fixing the denominator before a run.
Keep the generation pattern separate from its error-handling policy.

## Code to consult

Inspected 2026-11-01 at [`577ab5a`](https://github.com/oxwhirl/smacv2/commit/577ab5a2cff2391f8df582da5731ea9cd6adf3c6)
(commit dated 2024-02-15). Code inspection only; no StarCraft experiments reproduced.

| File at the inspected revision | Entry point and use |
|---|---|
| [distributions.py](https://github.com/oxwhirl/smacv2/blob/577ab5a2cff2391f8df582da5731ea9cd6adf3c6/smacv2/env/starcraft2/distributions.py) | `WeightedTeamsDistribution`, `ReflectPositionDistribution`, `SurroundedAndReflectPositionDistribution`, `MaskDistribution`: explicit scenario distributions |
| [wrapper.py](https://github.com/oxwhirl/smacv2/blob/577ab5a2cff2391f8df582da5731ea9cd6adf3c6/smacv2/env/starcraft2/wrapper.py) | `StarCraftCapabilityEnvWrapper.reset`: generation joined to reset |
| [starcraft2.py](https://github.com/oxwhirl/smacv2/blob/577ab5a2cff2391f8df582da5731ea9cd6adf3c6/smacv2/env/starcraft2/starcraft2.py) | `step`, `reward_battle`, `get_stats`: timing, learning reward and evaluation counters |
| [starcraft2.py observation and action methods](https://github.com/oxwhirl/smacv2/blob/577ab5a2cff2391f8df582da5731ea9cd6adf3c6/smacv2/env/starcraft2/starcraft2.py) | `get_obs_agent`, `get_state`, `get_avail_agent_actions`: local information, privileged training state and legal actions |

## What WH3 can borrow

Within the [index's transfer proposals](../benchmark-references.md#design-lessons-to-discuss):
declare the variation distribution, save realised starts, compare reactive controllers with
fixed timed plans, and report performance separately for different problem families.
Fresh samples within a family and reserved families answer different generalisation questions.

The real-world parallel is a team of robots with different capabilities and limited local
reports. Coordination is the shared problem; StarCraft combat and WH3 victories do not
validate physical robot behaviour. WH3 also controls groups through persistent high-level
orders, whereas SMACv2 controls individual units through discrete joint steps.
