# Designing WH3 benchmark scenarios

Owner direction, 2026-10-14: prioritize distinctive tactical challenges over balanced
general-purpose armies. Scenarios should give agents reasons to use specialist knowledge,
try unusual approaches and make difficult decisions. Battles should also be interesting
to watch. This is part of benchmark selection, not an optional showcase after calibration.

## Start with a tactical problem

Choose a faction-specific mechanic and one or a few **anchor units** whose use changes
the battle. Supporting units create decisions around that anchor: buy it time, expose a
target, protect a casting window, lure a counter away, or sacrifice something elsewhere.
An anchor can be ours or the enemy's. A roster of famous units is not sufficient if all
of them can simply attack the nearest target.

Give the agent a real disadvantage or constraint, and identify the obvious approach
that should be costly. Keep several plausible responses open; do not design every
battle around one secret trick. Write these as author hypotheses, not instructions in
the controller's prompt. Supply the actual public rules and capabilities consistently
to every controller, without revealing scoring state or suggesting a solution.

Each candidate records:

- The tactical question, faction mechanic, anchor units and why the support roster matters.
- The pressure: numerical odds, an unfavorable counter matchup, limited ammunition or
  magic, vulnerable objectives, terrain, or competing demands on the same units.
- Several plausible tactics and the decisions they demand. These are hypotheses until
  demonstrated in the original game; the benchmark need not prefer one winning style.
- Exact armies, lord mounts/loadouts, map, side, timer, difficulty/modifier and DLC;
  the observation/action features needed to use the specialist units properly.
- What a viewer should be able to recognize: a flank opening, a spell window, a rescue,
  a sacrifice, a breach, a capture or a reversal. Long inactivity is not interesting
  merely because a unit eventually survives the timer.
- A development variant and untouched held-out variations that test the same problem
  without reproducing its exact layout. Reversing sides is a different task when the
  objective changes, and needs its own setup and difficulty checks.

## First candidates

These are design briefs, not admitted or engine-verified scenario configurations.
Selectable cards, mounts, spell loadouts and mechanics must be checked before freezing.

| Candidate | Anchor and faction character | Decisions the setup should encourage |
|---|---|---|
| Cavalry facing anti-large infantry | A cavalry force with a few exceptional shock units, facing a dense spear/halberd line; verify the lord's mount before calling it fully mounted | Split the defense, choose engagement angles, coordinate charges, disengage before a losing grind, or defeat supporting threats first. Terrain and ranged pressure should prevent indefinite harmless circling. |
| A caster-led force | A powerful caster and a small support force, with the roster built around its actual lore, magic economy and faction mechanics; Tzeentch is an initial candidate | Create valuable spell targets, trade screening units for casting time, choose damage/control spells, protect or risk the caster, and manage a shared finite resource. The caster must matter beyond being another melee unit. |
| A siege against severe odds | A small defensive force with an anchor that can shift between threatened objectives; a separate attacker variant once breaching controls work | Allocate supplies, abandon or contest positions, create firing/spell opportunities, select a breach and time a committed assault. An attacker that cannot operate gates/walls/equipment is an interface failure, not a challenge. |
| Command a Skaven swarm | Many cheap bodies supporting a few unusual weapons, monsters or casters | Use expendable units to buy space/time, preserve the scarce damage source, choose acceptable losses and exploit the faction's asymmetry. Verify performance with the larger unit count. |
| Survive a Skaven swarm | A much smaller force with limited crowd-clearing anchors | Shape the approach, preserve ammunition/magic, prioritize threats inside the swarm and avoid encirclement. Large numbers alone must not turn the task into an uninformative loss. |

Cavalry and caster prototypes come first. The current Dwarf/Slaanesh Herald screens
remain useful harness and difficulty evidence; they do not satisfy this new selection
criterion automatically. Difficult sieges and the two swarm directions remain concrete
follow-ups, not a requirement to admit every family in the first release.

## Screen for useful decisions, then calibrate

Use `hold` and `attack_nearest` as transparent controls. Keep the existing `skills`
controller as a general scripted reference, but do not reshape every specialist task
until that particular script succeeds. It does not use every faction mechanic.
A competent reference may be the current LLM, a hybrid or a disclosed specialist script.
Its automation, prompts and tuning history must be recorded. Choose and freeze that
reference before the repeated comparison; one lucky model victory is insufficient.

Admission still requires repeatable setup, working required controls, evidence of a
viable strategy and repeated competent-versus-trivial separation with uncertainty.
For the initial calibrated development tier, target an intermediate success rate
(roughly 30–70%) for the declared competent reference. Harder challenge variants can be
kept separately, with their floor effects disclosed; they cannot substitute for a
discriminating initial benchmark. Keep failures and rejected candidates in the record.

Review traces for whether meaningful specialist decisions actually occurred. A win by
an unrelated trivial exploit or by a grossly superior anchor does not establish the
intended challenge. Report alternative successful approaches when observed. Keep this
qualitative review separate from authoritative outcomes and measured scores; do not
invent a numerical "creativity" or entertainment score.

After selecting the candidate/reference, freeze the repeated calibration and 0/6/10 s
added-age experiment in [calibration-plan.md](calibration-plan.md). Watchability must
come from the scenario and presentation: battles remain unpaused at 1x and evaluation
rules remain the same for every controller.
