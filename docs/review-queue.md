# Owner review queue

Decisions and completed work awaiting the owner's review. Current work stays in
[state.md](state.md#active-work); owner directions stay in [owner-direction.md](owner-direction.md).
Items keep their existing decision numbers. A listed choice or proposed check is not approval.

## Decisions

1. **Initial benchmark and the coordination suite.** The mirror is implemented, checked at `b1136e8` and lost by all eight arms' battles on version5; nothing has won it. The overnight [suite](twwarhammer3/benchmark.md#the-coordination-suite-suite-v1) adds twelve scenarios and compares control methods. Its choices are marked `JUDGEMENT` and wait for your review: which battles and calibration, which arms, and the proposed check. Handoff: `runs/coord-suite-20261104/handoff.md`.
2. **Next experiments and spending.** The suite's first comparison is exploratory, at one battle per pair. Choose whether to confirm it, on which arms and with what budget. Older P5, Kimi and team estimates are deferred; OpenAI's $52 cap still refuses Sol.
3. **Remaining autonomy rules.** The [standing menu and small interviews](autonomy.md#standing-work) were agreed on 2026-10-28; the saved overnight plan ran that night (02:39-04:35; [report](twwarhammer3/log.md#2026-10-28-overnight-restore-pauses-were-wsl-clock-steps-land-check-passes-at-dcb8b5a)). Other provisions of the older [away guidelines](autonomy.md) still await review; this was not blanket acceptance.
4. **Model-team choices to review later.** On 2026-10-28 you let me settle five open items for now; each keeps today's behaviour, stays marked and is listed in [multi-agent-implementation.md](twwarhammer3/multi-agent-implementation.md#choices-settled-for-now-2026-10-28). Before a paid team battle, agree a check for `team_llm_rules` ([next](twwarhammer3/multi-agent-implementation.md#next)); model members have not played live.
5. **Campaign permissions.** Separately allow or refuse harness saves and irreversible Steam achievements. These choices are required before any campaign launch. Deferring keeps campaign work to [offline drafts](autonomy.md#wh3-campaign-infrastructure).
6. **Controller direction.** Adopt or drop the attack-route prompt change; keep or defer the commander approach. The attack-route draft needs its own comparison under the new Land Battle definition and renumbering before adoption. `commander` is unplayed since v4; [controller plans](twwarhammer3/controllers.md) remain proposals.
7. **Backend and sampling policy.** Review the delegated backend pins and decide sampling capture and serving-fault treatment. b36's [backend pins](twwarhammer3/latency.md#owner-decisions) await review. Recommended: request log-probabilities, seed and explicit sampling where the pinned backend advertises them ([gaps](posttraining.md#beyond-supervised-fine-tuning); listings rechecked October 21, not a capture test). Choose how to report or rerun [garbled replies](twwarhammer3/empire.md#for-the-owner-to-decide); current backend failures count against the model.
8. **Training preparation.** Choose a host, serving route and teacher; decide when and how to build the Empire dataset. Secondary priority. [Data-use choices](posttraining.md#provider-terms): OpenAI outputs (25,503 rows excluded: Spire 11,099; WH3 14,404), GLM-5.3 or rejection-sampled Qwen3.6; Step 5 weights are public. An [Empire content screen and dataset timing](twwarhammer3/empire.md#for-the-owner-to-decide) are still needed. Smoke checks establish no learning gain.
9. **Spire's next step.** After WH3, run one meaningful comparison or freeze this track; the state-restore investigation comes first (owner, 2026-10-23). Also noted for later: the capture check (owner, 2026-10-23: "Not sure what this is"). Both, with the proposed comparison and the data-night choice: [Spire open decisions](spire/fullrun/README.md#open-owner-decisions).
10. **Thesis and RL environment.** Likely multi-agent systems, possibly multi-agent RL; no research question selected (owner, 2026-10-28). Tentative environment: each agent sees its available battle state, perhaps teammate information, controls its army share and learns from sparse win/loss near restored endings. Reset may use a battle start or checkpoint; details and correctness checks are for later. [Direction 6](thesis/directions.md#6-wh3-as-an-rl-environment-for-high-level-decisions); [research shortlist](thesis/directions.md#what-the-2026-10-28-checks-changed). Human-AI work stays a note; licensing is deferred.
11. **Local LLM checkpoint RL — deferred.** Leave this post-training experiment paused (owner, 2026-10-28). No recovery choice is needed now; the existing results and choices remain for a future review. Merged on 2026-10-28. [Details](twwarhammer3/checkpoint-rl.md#open-owner-choices-decision-11).
12. **Light factory follow-ups.** Earlier answers are [carried out](twwarhammer3/log.md#2026-10-29-evening-the-owners-light-factory-answers-carried-out); Codex's completed audit is in `runs/factory-assessment-20261031/handoff.md`. Commit guard approved 2026-10-30. Two night decisions remain in `runs/overnight-20261030/handoff.md`: the test edits; whether `check.py`'s own edits need your yes.

## Completed work and handoffs

Factory: [workflow.md](workflow.md), stages 1-4 built; stage 5 awaits the next experiment.
CI runs `check.py` on each push to `main` and each pull request (results: `gh run list`).

MARL references: [three papers plus ProgramLab](thesis/papers.md#marl-implementation-references-2026-10-28), inspected 2026-10-28; ProgramLab's training code is still unreleased (rechecked 2026-10-31). No external tests or learning results reproduced.

Codex: [WH3 tactics](twwarhammer3/tactics-reference.md) and [evaluation proposals](twwarhammer3/tactics-evaluation.md) saved; source review in `runs/tactics-reference-20261101/`. Follow-up: shared Codex/Claude WH3 knowledge skill ([reminder](owner-direction.md)). [Benchmark references](twwarhammer3/benchmark-references.md) saved: BEHAVIOR, CARLA and SMACv2 construction, evaluation and pinned code; source review in `runs/benchmark-references-20261101/`. Research ran no games and adopted no benchmark choices. [GaP](twwarhammer3/gap-plan.md) temporary initiation check passed offline at `4f0c3fc`; one fresh 1x battle at `5c02d08` passed infantry-contact/cavalry-melee criteria but lost at 666.8 s. Game closed; no strength claim. [New battle viewer](http://localhost:8765/gap-fixed-live-20261101.html). Recorded spend $0.02857/$5; `runs/gap-initiation-20261101/handoff.md`; benchmark choices deferred.

Codex testing audit: [PR #1](https://github.com/nivaldoh/slay_the_spire_ai/pull/1) merged 2026-10-31 (`0a17026`); check-edit/CI decisions wait (`runs/test-quality-20261031/`; factory assessment: `runs/factory-assessment-20261031/handoff.md`).
[Native multiplayer](twwarhammer3/native-multiplayer.md#implementation-status) build decisions: `runs/wh3-native-mp-20261030/handoff.md`; observer smoke ran 2026-11-01 in one single-player battle: your orders obeyed, every card reading as expected (n=1, unverified; [log](twwarhammer3/log.md#2026-11-01-native-multiplayer-observer-smoke-one-battle)).

Claude Code's long run (2026-10-31): all four agreed live checks passed at `96bb137` (Land and
team also failed in between, on a UI stat and on WSL clock jumps); b52, an unused outcome scorer,
compare-peers fixes and the 10-30 factory items merged; branches and decisions in `runs/overnight-20261031/handoff.md` ([log](twwarhammer3/log.md)). $0.

Built (Claude Code, 2026-11-01 night): the "How the code works" [plan](how-code-works-plan.md)'s pilot (map, play-job story, `check.py` flags; merge `c471b45`)
and step 4 (two stories; merge `45c2a39`), reviewed by agents; quiz not passed (n=1). Your look waits: `runs/how-code-works-20261101/handoff.md`. Then (11-01 afternoon) two tabs, "Control methods" (basic vs GaP on one battle clock) and "One graph battle" ([log](twwarhammer3/log.md#2026-11-01-control-methods-drawn-on-the-how-the-code-works-page)); reviewed by agents, no quiz, your look waits (`runs/control-methods-20261101/handoff.md`). $0. Then (11-01 evening) the page [redesigned](twwarhammer3/log.md#2026-11-01-the-how-the-code-works-page-redesigned): one bar, map dots at real rates, a whole-battle GaP replay; three old tabs removed. $0.

Built (Claude Code, 2026-10-31): `--provider anthropic` in both games (Haiku, Sonnet, Opus 5.5; [plan](anthropic-provider-plan.md)); every effort passed one live call at `551b514` ($0.02, [log](twwarhammer3/log.md#2026-10-31-anthropic-provider-added)). Jobs need `GAMEAI_ANTHROPIC_WORKSPACE_ID` too; no battle or run yet.

Testing reviews: [eval review](twwarhammer3/log.md#wh3-evaluations-and-tests-2026-10-23), [live-check comparison](twwarhammer3/log.md#wh3-live-check-comparison-2026-10-23).

### Cleanup 2026 11 02

The 19 cleanup commits are merged and pushed (`8211df9..515491c`); the recorded owner
answers were to merge all and accept both flagged edits. The agreed check that the suite
rejects its kept wrong versions was recorded at `607675e`; its revision and dirty-tree
limits are in [agreed-checks.md](agreed-checks.md).

The tactics pages were committed at `386802b`; the untracked-target link rule landed at
`d605605`. The rule catches an already committed page's missing target on the next run;
it does not reject the first commit that omits a new target (its marker documents this limit).
The GaP empty-reply question remains in `runs/cleanup-20261102/handoff.md` and, since
`6c46b08`, as an open question in [gap-plan.md](twwarhammer3/gap-plan.md) (owner: decide later).
That handoff's unmerged/untracked-page status predates these commits.
