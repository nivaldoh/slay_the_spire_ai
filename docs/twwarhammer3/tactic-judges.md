# Research plan for judging WH3 tactics

Owner, 2026-11-04: help decide how to check what scenarios measure, including whether an
LLM judge could detect tactics. **Research and proposal only.** No judge, rubric, acceptance
threshold or evaluation is adopted. The [scenario plan](scenario-guidelines.md#current-plan-and-owner-decisions)
starts with a simpler scenario, then a more complex one after the first is ready.

An LLM could read structured records; a vision-language model (VLM) could also inspect
frames. Both are candidates for narrow event annotations, not established WH3 judges.
Separate three questions: was a tactic attempted, did its observable steps occur, and did
it help? Orders can establish an attempt. State and imagery may establish execution.
Neither an attractive manoeuvre nor a judge's explanation establishes benefit or necessity.
Those claims still need the [scenario's comparison](scenario-guidelines.md#establish-that-the-intended-decision-matters).

## What existing research supports

Primary sources read and independently checked on 2026-11-04. These are method references,
not replications or evidence of accuracy in WH3. Audit: `runs/scenario-plan-update/research-audit.md`.

| Source | What it actually judges and sees | Useful idea and limit for WH3 |
|---|---|---|
| [GVL: Vision Language Models are In-Context Value Learners](https://arxiv.org/html/2411.04549v1), §§3–4 | A frozen VLM estimates task progress from sampled, shuffled frames, an initial-frame anchor and task text; examples can help | A task-specific visual progress question can be more concrete than a generic quality score. Progress is not tactic correctness. Do not copy its shuffling into a test that needs the manoeuvre's temporal order |
| [AHA: A Vision-Language-Model for Detecting and Reasoning Over Failures in Robotic Manipulation](https://arxiv.org/html/2410.00371v1), §§3–4 | A fine-tuned VLM sees a collage of temporal/multicamera keyframes and subtask text; FailGen creates failures by perturbing successful trajectories | Include believable near-misses, not only obvious successes. Its training and robot-specific evidence are not an off-the-shelf WH3 capability |
| [MINERVA: Evaluating Complex Video Reasoning](https://arxiv.org/html/2505.00681v1), §5.1 | MiRA judges candidate reasoning against text references using temporal, perceptual, logical and completeness criteria; the judge itself does not inspect the video | Explicit criteria and human comparison are useful. Reference-based reasoning agreement does not validate a judge as an independent observer of a battle |
| [VideoJudge: Bootstrapping Enables Scalable Supervision of MLLM-as-a-Judge for Video Understanding](https://arxiv.org/html/2509.21451v1), §§3–6 | A trained visual judge sees video frames, an instruction and candidate answers; it judges answer quality | Evidence selection and frame budget matter. Answer quality is a different target from whether a charge or protection event occurred; no frame count transfers automatically |
| [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/html/2306.05685v4), §§3.3–3.4 | Text judges compare assistant responses; presentation can bias preferences | Hide identities and test swapped answer order and confident unsupported prose. Its agreement results are not WH3 validation |
| [Don't Read the Log](https://arxiv.org/html/2609.28564v1), §§3–6 | Verifiers see fixed video frames with different execution narratives; effects differ substantially by model | Distinguish trusted engine facts from the agent's claims about success. This recent preprint uses a small author-labelled set and one open-model family, with much smaller effects on tested closed models; it does not show that all logs or judges are unreliable |

The existing [review guidance](evaluation-guidelines.md#10-later-human-review-llm-judges-rubrics-and-training-rewards)
already proposes narrow rubrics, blind labels, held-out judge checks and bias tests.
This plan extends its earlier text-only scope to consider visual event evidence.
[MultiAgentBench](benchmark-references/multiagentbench.md) also separates task outcomes
from judged process. None supplies a ready-made WH3 tactics score.

## Proposed role and evidence

JUDGEMENT: Judge role — Codex, 2026-11-04: proposes offline, evidence-citing annotations
for specific events, initially outside the ranking. A judge-derived tactics score differs;
claims and any later ranking use depend on the owner choosing and validating that role.

The following proposal rests on JUDGEMENT `docs/twwarhammer3/tactic-judges.md` Judge role.
Use engine records for the ending, health, resources and other directly recorded facts.
Check the recorder/detector itself before treating its output as a reference. Consider a
judge only for a question that needs interpretation across records or visual observations.
Its outputs would be inspected after the battle, not fed back to the controller.

Examples to discuss after selecting the first scenario, not required initial tactics:

| Question | Evidence that could support it | A near-miss the method must distinguish |
|---|---|---|
| Did this unit disengage and charge again? | Identified unit and target, initial contact, separation, return and renewed contact over time | Repeated attack orders while trapped in the original melee; a retreat without return. Contact alone does not establish a charge bonus |
| Did this screen protect useful ranged units? | Threat path, screen engagement and ranged-unit activity over the relevant interval | Guns survive because the threat went elsewhere, or stay safe but never contribute. Observed protection still does not establish its causal value |

JUDGEMENT: Judge evidence — Codex, 2026-11-04: proposes comparing structured records alone
with records plus synchronized imagery for a chosen question. These views can yield different
labels; detection claims depend on the selected evidence and its missing-data rules.

This comparison rests on JUDGEMENT `docs/twwarhammer3/tactic-judges.md` Judge evidence.
Start with the smallest useful packet: a declared interval, consistent unit IDs, timestamped
states, issued orders, acknowledgements and independently observed effects. Add synchronized
frames or clips where they expose something the records do not. Acknowledgement is not
execution. Nearby centres do not prove contact or a flank. Neither net damage nor ammo
spent identifies who hit whom without further evidence.

Keep engine facts, derived detector output and the player's own explanations distinguishable.
Hide model/arm names, proposed verdicts and the final result when they are irrelevant to the
question. Do not silently remove a result needed by the rubric itself. Treat embedded
instructions and success claims as data, not directions to the judge. Evaluator-only state
may check what happened, but judging whether a choice was reasonable requires the information
available to that player. Never send private recording or judge evidence to a live policy.

Proposed answer: **observed / not observed / unclear / not applicable**, with unit IDs,
time interval, supporting evidence, contradictions and missing information. The rubric must
define those distinctions. Missing frames are not a negative label. Avoid free-form
“good tactics” scores or an uncalibrated confidence number.

For the owner's manual demonstrations, record pause use and both battle and wall time.
A pause is not a tactical delay or idle manoeuvre. Human demonstration labels remain separate
from automated-controller results. The capture method still needs agreement.

## How we could check a judge before relying on it

This is a proposed procedure to discuss for the first actual question, not an agreed check:

1. Write a short rubric with observable steps, relevant engine mechanics, positive examples,
   near-misses and ambiguous cases. Ask the owner to label selected evidence before seeing
   the judge's answers. The owner's reference alone is a single human's judgement, not
   human consensus. Another human or a later blind relabelling can help examine ambiguity;
   another AI is not an independent human reference.
2. Develop the rubric on one group of battles and assess it on separate battles/launches.
   Neighbouring frames from the same fight must not straddle that boundary. This proposed
   judge-calibration split does not settle the undecided reservation policy for benchmark
   scenarios. State how examples were sampled; a deliberately difficult collection does
   not estimate the error rate in ordinary battles.
3. Compare a simple record-based detector, an LLM reading records and a VLM with imagery
   where each can answer the same question. Measure correct unit/time identification as
   well as the label. Start without training a custom model. Select models, evidence
   budgets and pass criteria before those comparisons; none is chosen here.
4. Report false positives, false negatives, precision/recall, unclear/not-applicable counts
   and coverage per tactic with the underlying counts. Include uncertainty and the number
   of independent battles, not just clips. Accuracy on answered items can hide excessive
   abstention. Preserve human disagreements and errors concentrated in particular scenarios.
5. Challenge the method with renamed IDs, hidden model names, swapped candidate order when
   applicable, unsupported confident narratives, instructions inside logs, acknowledged
   but blocked orders, missing frames and ambiguous contact. A disrupted temporal sequence
   should change or invalidate a temporal judgement, not necessarily preserve its label.
6. Freeze rubric, judge/model version, prompt, evidence selection, sampling and any repeat
   aggregation before confirmation. Retain every answer; do not retry until the label looks
   right. Recheck relevant changes before carrying the claim forward. Repeated calls on
   one item measure judge consistency, not independent battle performance.

If it cannot separate the chosen event from its near-misses, simplify the question, improve
the evidence, retain human review or drop that label. A useful judge may save annotation
time without becoming part of the score. A validated occurrence label would still leave
“did it help?” and “does this scenario test something interesting?” as separate questions.

## Decisions needed when the first scenario is concrete

Choose the actual decision to observe, its evidence and reference labels, then agree what
errors would make the annotation unusable. Decide whether the benefit justifies its cost
and latency. No model choice, sample count, acceptance threshold, ranking weight, training
plan or game session follows automatically from this research.
