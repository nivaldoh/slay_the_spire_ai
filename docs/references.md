# References

Outside sources for how we build, check and run things: agent workflow, verification, testing,
evaluation and research-code practice. Thesis related work lives in
[thesis/papers.md](thesis/papers.md); testing examples to imitate are also in
[testing.md](testing.md#references-worth-using). Add a source here when it shapes a plan or a
rule, with one line on what it says.

## Haengju siege evaluation plan (2026-11-08)

For the [second evaluation battle plan](twwarhammer3/haengju-eval.md). Each source guides the design
and says nothing about the engine. Status as in the next section.
- Encyclopedia of Korean Culture, [행주대첩](https://encykorea.aks.ac.kr/Article/E0062859): two
  palisade lines and earth banks, under 10,000 Koreans with 1,000 monk soldiers, about 30,000
  ("3만여 명") Japanese in seven divisions from about 6 a.m., the northwest breach and Gwon Yul's
  counterattack, the arrow shortage and Yi Bin's two boats. Read, through a translating fetch.
- Wikipedia, [Battle of Haengju](https://en.wikipedia.org/wiki/Battle_of_Haengju), citing Hawley,
  *The Imjin War* (2005), pp. 318-323: about 2,300 against about 30,000, attacks in turn because
  of limited space, Ukita's and Kobayakawa's breaches, 10,000 arrows by boat. Secondary.
- M. G. Haynes, [Military Heritage article](https://warfarehistorynetwork.com/?p=100625): narrow
  approach and hwacha on the heights. Read; a popular article that cites no sources.
- Wikipedia, [Siege of Eger (1552)](https://en.wikipedia.org/wiki/Siege_of_Eger_(1552)),
  [Siege of Jinju (1592)](https://en.wikipedia.org/wiki/Siege_of_Jinju_(1592)),
  [Siege of Belgrade (1456)](https://en.wikipedia.org/wiki/Siege_of_Belgrade_(1456)) and
  [Siege of Izmail](https://en.wikipedia.org/wiki/Siege_of_Izmail): figures for the rejected
  candidates (Belgrade's sortie "by some accounts" spontaneous; Izmail 31,000 against 35,000 in
  the article's text). Secondary.

## Communication structure in one army (2026-11-08)

For the [peer and commander study](twwarhammer3/communication-structure.md). Status: "read" means
one agent fetched the page and saw the cited numbers; "secondary" means only a summary or a
replication was available; "abstract" means only the abstract was read.

Human groups and command and control:
- Bavelas 1950, [Communication patterns in task-oriented groups](https://pubs.aip.org/jasa/article/22/6/725/646415/Communication-Patterns-in-Task-Oriented-Groups),
  J. Acoust. Soc. Am. 22(6). Chain, circle, star and Y networks of five on a common-symbol task.
  Secondary (a [course blog summary](https://blogs.cornell.edu/info2040/?p=20033)): star and Y groups
  were the most efficient.
- Leavitt 1951, *Some effects of certain communication patterns on group performance*,
  J. Abnorm. Soc. Psychol. 46. Wheel against circle, 15 trials per group. Secondary: Sidi's 1970
  replication thesis ([PDF](https://digitalarchive.library.bogazici.edu.tr/bitstreams/e4c11fcf-4610-49ef-ac33-1537cf0cf854/download),
  Table 17) gives Leavitt's mean of the three fastest trials as 31.8 s for the wheel and 49.8 s for
  the circle.
- Shaw, communication network reviews, as summarized in
  [course notes](https://pages.uoregon.edu/mauro/psy457/comnets.htm): centralized networks are faster
  on simple tasks, decentralized ones on complex tasks, explained by saturation of the central
  position. Secondary.
- Guetzkow and Simon 1955, [The impact of certain communication nets](https://ideas.repec.org/a/inm/ormnsc/v1y1955i3-4p233-250.html),
  Management Science 1(3-4): a network shapes how a group organizes itself as well as how it does
  the task. Abstract.
- Leweling and Nissen 2007, [Hypothesis testing of edge organizations](https://internationalc2institute.org/s/12th-T5-017.pdf),
  12th ICCRTS. ELICIT with 68 people in four groups (one played only as an edge organization, one
  only as a hierarchy, two played both): edge time score 0.47 against 0.33 for hierarchy (p<0.001,
  210 identifications), accuracy 0.69 against 0.66. Peer factoid sharing stayed open in the
  hierarchy arm. Read.
- Manso and Ruddy 2013, [Comparison between human and agent runs in the ELICIT N2C2M2 validation
  experiments](https://internationalc2institute.org/s/18th-T5-041.pdf), 18th ICCRTS. A coordinator who
  alone sees every team's site scored 0.34 with humans against 0.80 for collaboration (4 runs
  each), and 0.97 against 0.99 with software agents (27 runs each), out of 18 human and 135 agent
  runs over five approaches. Read.
- US Army, [ADP 6-0 mission command announcement](https://www.army.mil/article/225414/combined_arms_center_launches_new_mission_command_doctrine),
  2019: mission command "empowers subordinate decision making". Secondary; the doctrine PDF was not
  reachable.
- Graicunas 1933, span of control, via [Nickols](https://nickols.us/graicunas.htm): counts 100
  relationships for five subordinates and advises at most five. Secondary, theory only.

Multi-agent RL with communication:
- Sukhbaatar et al. 2016, [CommNet](https://arxiv.org/abs/1605.07736): a learned broadcast channel.
  Abstract.
- Foerster et al. 2016, [RIAL and DIAL](https://arxiv.org/abs/1605.06676): learned protocols under
  partial observability. Abstract.
- Singh et al. 2019, [IC3Net](https://arxiv.org/abs/1812.09755): a learned gate on when to talk. On
  the hard traffic junction with zero vision it scored 72.4% against CommNet's 50.2%, with the gate
  fixed open for that task, so that gain comes from per-agent rewards. Read.
- Das et al. 2019, [TarMAC](https://arxiv.org/abs/1810.11187): addressed messages; hard traffic
  junction 84.6% with one round and 97.1% with two, against 74.1% without communication. Read.
- Niu et al. 2021, [MAGIC](https://archive.illc.uva.nl/AAMAS-2021/pdfs/p964.pdf), AAMAS: a learned
  communication graph. Its [code](https://github.com/CORE-Robotics-Lab/MAGIC/blob/0ad3a6126f46e475f8d46ab61e67fddbfe99e7d8/magic.py)
  masks an adjacency matrix by which agents are alive, the pattern the study's router follows. Read.
- Kong et al. 2017, [MS-MARL](https://arxiv.org/abs/1712.07305): a master with the global state and
  slaves with local state; StarCraft win rates above CommNet (for example 0.77 against 0.68). Read.
- Gupta et al. 2021, [HAMMER](https://arxiv.org/abs/2102.00824): one central agent with the full
  state messages local agents that cannot message each other, on cooperative navigation and
  multi-agent walker. Read.

LLM agent teams and topologies:
- Chen et al. 2024, [Scalable multi-robot collaboration with large language models: centralized or
  decentralized systems?](https://arxiv.org/abs/2309.15943),
  ICRA: peer dialogue worst and a central planner with per-robot checks best, for example 25.0%
  against 82.5% on BoxNet1, 40 runs per task. Read (also cited in team-structures.md).
- Guo et al. 2024, [Embodied LLM agents learn to cooperate in organized teams](https://arxiv.org/abs/2403.12482):
  a designated leader made three GPT-3.5 agents 9.76% more efficient (p<.05, 20 seeds). Read.
- Zhang et al. 2023, [CoELA](https://arxiv.org/abs/2307.02485): decentralized LLM agents where each
  message costs a time step. Read.
- Qian et al. 2024, [MacNet](https://arxiv.org/abs/2406.07155): chain, star, tree, mesh and other
  graphs on offline tasks; "no single topology consistently excels". Read.
- Zhu et al. 2025, [MultiAgentBench](https://arxiv.org/abs/2503.01935): in its Research scenario,
  star and graph-mesh protocols gave similar task scores and tree (a planner over sub-planners) the
  lowest. Its [code](https://github.com/ulab-uiuc/MARBLE/blob/8d60fa17b5596b44458a52d4296061b9fc13d6f2/marble/agent/base_agent.py)
  lists allowed recipients as an enum but its handler checks only that the sender has some link.
  Read.
- Zhuge et al. 2024, [GPTSwarm](https://arxiv.org/abs/2402.16823): optimizing links cuts adversarial
  agents out of a swarm. Read.
- Zhang et al. 2024, [AgentPrune](https://arxiv.org/abs/2410.02506): pruning redundant messages cuts
  tokens. Abstract.
- Zhang et al. 2024, [G-Designer](https://arxiv.org/abs/2410.11782): with five GPT-4 agents the star
  averaged 82.07 and the complete graph 86.55 over six benchmarks. Read.
- Cemri et al. 2025, [Why do multi-agent LLM systems fail?](https://arxiv.org/abs/2503.13657), MAST:
  1,642 traces; withholding information 0.85% and ignoring another agent's input 1.9% of failures.
  Read.
- Li et al. 2024, [LLM-PySC2](https://arxiv.org/abs/2411.05348): StarCraft II, stepped by the
  environment, which waits up to a set time for every agent's reply, with commander and executor
  agents and per-agent message targets; reports noisy messages and blind
  trust, with no controlled topology comparison. Read.

## CaP-X: code-as-policy and WH3 (2026-11-06)

Added at the owner's request for later research. Letian (Max) Fu et al.,
*CaP-X: A Framework for Benchmarking and Improving Coding Agents for Robot Manipulation*,
ICML 2026, PMLR 306:32155–32212.
[Publication and BibTeX](https://proceedings.mlr.press/v306/fu26u.html) ·
[Paper v2, 2 July 2026](https://arxiv.org/html/2603.22435v2) ·
[PDF v2](https://arxiv.org/pdf/2603.22435v2) ·
[Project](https://capgym.github.io/) · [Code](https://github.com/capgym/cap-x).

**What it studies.** A model writes executable Python that combines robot perception and
control APIs. CaP-Gym supplies the environments; CaP-Bench varies API abstraction,
single-turn versus multi-turn interaction, and perceptual feedback. Its core study covers
12 models and seven tasks, with 100 trials per task/tier. Success depends strongly on
human-provided abstractions. CaP-Agent0 adds textual descriptions of visual changes,
reusable synthesized helpers and an ensemble of candidate programs. CaP-RL updates the
coding model with GRPO and environment rewards; its training uses privileged state APIs.
See [sections 2–5 and Table 1](https://arxiv.org/html/2603.22435v2#S2).

**Possible WH3 connections — our interpretation, unverified:**

| Connection | Why it matters here and what remains open |
|---|---|
| Attribute capability to the right component | Our direct-order models, `commander`/`Skills` and [GaP graphs](twwarhammer3/gap-plan.md) receive different supplied behavior. A comparison could vary the amount of helper logic while keeping observations and basic orders fixed. A successful hand-written tactic inside a skill cannot by itself establish model planning ability. |
| Generate a policy that keeps reacting | The [generated-rule proposal](twwarhammer3/robotics.md#1-compare-parameter-selection-with-generated-feedback-rules) could produce a bounded controller for retargeting or disengagement, evaluated against fixed scripts and model-selected parameters. Generated Python is broader than our current graph interface; adopting it would require a separate execution and information-boundary design. |
| Recover from execution feedback | Our structured observations could describe permitted changes such as a friendly unit routing or a visible target disappearing. Such feedback might support revising a program or graph. Order acceptance alone cannot establish tactical success; current visibility and fresh state still matter. |
| Reuse skills and revise between battles | Successful development attempts could supply reusable helpers or graph fragments. The existing [GaP authoring/revision distinction](twwarhammer3/gap-plan.md#three-activities-and-later-research-questions) is relevant. Later comparisons would need to disclose helper provenance and separate development battles from held-out evaluation. |
| Study learning and team control separately | CaP-RL is a reference for the [learning-feasibility question](twwarhammer3/research-focus.md#learning-under-limited-throughput). Changing model weights, revising a saved program and commanding independent unit groups are different activities. An ensemble that writes one program does not establish cooperation among independently acting WH3 teammates. |

**Limits that matter for WH3.** The paper's multi-turn trials continue without resetting
the environment; its human reference programs were refined offline. Its reported timing
measures program generation and whole attempts, rather than a motor command's latency
([section 3, Appendix K](https://arxiv.org/html/2603.22435v2#A11)).
For WH3, recovery must occur in an unpaused 1x battle while the opponent acts. Any future
comparison would need to account for observation age, inference and helper-model cost,
and preparation/retry budgets. The paper does not establish that extra reasoning pays off
under those conditions. Our engine already handles pathfinding and fighting, so its
robot API tiers are not equivalent to WH3 order tiers. Visual differencing suggests a
feedback representation; it does not justify exposing replay images, hidden enemies or
`evaluation`/`final`/`setup` to a policy. Likewise, its privileged RL training and shared
robot APIs do not establish WH3-to-robot transfer or affordable WH3 training.

Read sections 2–3/Table 1 for evaluation design, section 4/Appendix H for the agent,
section 5 for post-training, and Appendix K for human-baseline and cost caveats.
Source inspection: paper v2 sections 2–5 and Appendix K, publication record and repository
README, 2026-11-06. Audit: `runs/cap-x-reference/source-audit.md`.
No external results reproduced, WH3 experiment run or verification method adopted.

## WH3 research focus (2026-11-06)

The [focus spec](twwarhammer3/research-focus.md#reading-map-and-decisions) reuses these
sources from the existing collection. Primary abstracts were re-read and independently
checked for the narrow claims used; selected SMACv2, RoCo and IQL sections were also checked.
Quotes and limits: `runs/wh3-research-focus/review/source-review.md`. No results reproduced.

- [CheckList](https://aclanthology.org/2020.acl-main.442/): capabilities and test types
  organise behavioural testing; the WH3 categories remain proposals.
- [SMACv2](https://arxiv.org/abs/2212.07489): timestep-only policies can win original SMAC
  scenarios, motivating a test of whether fresh observations matter.
- [Reasoning or Reciting?](https://arxiv.org/abs/2307.02477): changed task assumptions probe
  transfer; they do not identify a model's training data.
- [RoCo](https://arxiv.org/abs/2307.04738): LLM dialogue and robot task dependencies are
  relevant analogies, without a WH3 transfer claim.
- [IQL](https://arxiv.org/abs/2110.06169): offline learning without querying values of unseen
  actions; the availability of this method does not establish that WH3 traces suffice.
- [Statistical Precipice](https://arxiv.org/abs/2108.13264): few-run point estimates can hide
  uncertainty; no WH3 sample count or statistical method is selected by the focus spec.

## Cannae evaluation proposal (2026-11-05)

For the [candidate plan](twwarhammer3/cannae-eval.md), not a live-game verification:
- Polybius, [Histories 3.113–116](https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Polybius/3%2A.html#113),
  Paton translation, Loeb 1922: advanced centre, inward-turning infantry and cavalry
  redeployment. In 3.115 the Romans are "caught between the two divisions of the enemy";
  in 3.116 Hasdrubal "led his squadrons on to where the infantry were engaged".
  Historical motivation only; this does not establish WH3 withdrawal or encirclement effects.
  Fordham's [sourcebook heading](https://sourcebooks.web.fordham.edu/ancient/polybius-cannae.asp)
  identifies the event as "The Battle of Cannae, 216 BCE".
- Ellis et al., [SMACv2](https://arxiv.org/abs/2212.07489v2), abstract: "an open-loop policy
  conditioned only on the timestep can achieve non-trivial win rates for many SMAC scenarios".
  Motivates a fixed-plan control; no WH3 conclusion follows from its StarCraft findings.
- [SMACv2 wrapper.py at 577ab5a](https://github.com/oxwhirl/smacv2/blob/577ab5a2cff2391f8df582da5731ea9cd6adf3c6/smacv2/env/starcraft2/wrapper.py),
  `StarCraftCapabilityEnvWrapper.reset`: merges generated configuration before resetting.
  Reference for materialized variants; its automatic reset retry and stepped clock are not
  adopted. The existing [profile](twwarhammer3/benchmark-references/smacv2.md) gives context.
  Source and code audit: `runs/cannae-eval-plan/`; no upstream experiments reproduced.

The [recognition/adaptation comparison](twwarhammer3/cannae-comparison.md), 2026-11-05,
uses the same SMACv2 fixed-plan warning and code reference, plus:
- Ribeiro et al., [CheckList](https://aclanthology.org/2020.acl-main.442.pdf), section 2.2:
  directional tests expect a label to "change in a certain way". This motivates testing
  whether a changed WH3 situation reverses a useful choice; that reversal needs engine evidence.
- Cobbe et al., [Procgen](https://arxiv.org/abs/1912.01588), abstract: a benchmark of
  "16 procedurally generated game-like environments" for "sample efficiency and generalization".
  Motivates a declared exposure boundary, not a claim that generated WH3 cases are valid,
  difficult or absent from pretraining. Follow-up source/design audit: `runs/cannae-improvisation/`.

For [battle C's limited communication design](twwarhammer3/cannae-communication.md),
sources inspected 2026-11-05; no upstream experiment reproduced:
- Polybius 3.114–116 above: command at centre/wings, local response by flanking infantry,
  and Hasdrubal's redeployment motivate distributed execution and initiative. These passages
  do not specify a message log, codebook, range or latency for Cannae.
- Polybius, [Histories 6.40](https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Polybius/6%2A.html#40),
  Paton translation: "On the second signal they load the pack animals". Successive Roman
  camp-departure signals illustrate prearranged meanings, not Hannibal's battlefield protocol.
- [SMAC `smac/env/starcraft2/starcraft2.py`](https://github.com/oxwhirl/smac/blob/master/smac/env/starcraft2/starcraft2.py),
  `get_obs_agent` docstring: "Agents should have access only to their local observations".
  Research-code reference for the member-information boundary; its unit perception and
  stepped environment do not establish WH3 local sight or its asynchronous timing.
- The same file's `get_agent_action_heuristic` keeps a selected target until unavailable.
  Code-structure reference for A's scripted witness target memory; WH3 uses only current
  visible, able contacts. Its tactical strength and global enemy access do not transfer.
- Das et al., [TarMAC](https://proceedings.mlr.press/v97/das19a.html), abstract distinguishes
  "what messages to send and whom to address them to". Motivates content/recipient controls;
  its rounds before environment actions are not adopted in an unpaused WH3 battle.
- [Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs#json-schema-limitations),
  checked 2026-11-05: array `maxItems` is unsupported. C omits that wire keyword for
  Anthropic while retaining its parser/dispatcher bound. [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs#supported-schemas)
  supports the keyword on the standard models here; C retains it for that provider.
  Documentation and fake transport checks do not establish real provider acceptance.

## Flying reserve construction sources (2026-11-05)

- SEGA/Creative Assembly [Bretonnia Steam description](https://store.steampowered.com/app/534330/Total_War_WARHAMMER__Bretonnia/):
  publisher-controlled 2017 roster names Pegasus/Royal Pegasus/Royal Hippogryph flying
  cavalry. Historical category evidence, not current stats or host recruitment. *Read.*
- Creative Assembly [Deployment and terrain tutorial](https://academy.totalwar.com/battle-deployment-and-battle-terrain/):
  generic deployment, concealment and high-ground discussion; no oracle for this map's
  ground or air routes. *Read.*
- RPFM [schema repository](https://github.com/Frodo45127/rpfm-schemas), `schema_wh3.ron`
  at `42290ba010661ce3ac426a307fd8d6b3ea0f2c5b`: existing `scripts/wh3_db.py` decoded
  current-build main/land unit records with no leftover bytes. Task-local schema/hash
  and raw evidence stay under `runs/cannae-build/research/`; no tool installed. *Used.*

## Tactic-judge research (2026-11-04)

For the [WH3 judge proposal](twwarhammer3/tactic-judges.md). All six sources independently
fetched and excerpts checked; audit `runs/scenario-plan-update/research-audit.md`. No result
reproduced and no WH3 judge validated.
- [GVL](https://arxiv.org/html/2411.04549v1): estimates task progress with a frozen VLM and
  shuffled trajectory frames; temporal-progress agreement is not tactic correctness.
- [AHA](https://arxiv.org/html/2410.00371v1): fine-tuned visual failure annotation using
  keyframe collages and generated failure cases; its robot task evidence does not transfer automatically.
- [MINERVA/MiRA](https://arxiv.org/html/2505.00681v1): explicit reasoning criteria and text
  reference judgements; MiRA itself does not inspect video, so it cannot validate WH3 perception.
- [VideoJudge](https://arxiv.org/html/2509.21451v1): frames and candidate answers support
  answer-quality judging; evidence/frame selection matters, but the task is not tactic detection.
- [MT-Bench judge](https://arxiv.org/html/2306.05685v4): presentation biases motivate blind
  labels, ordering checks and independent references; chatbot preference agreement is not event accuracy.
- [Don't Read the Log](https://arxiv.org/html/2609.28564v1): preliminary, model-dependent
  effects of execution narratives on fixed-video judgements; motivates testing unsupported
  success claims, not discarding verified engine telemetry.

## Empirical and formal verification (2026-11-03)

For [testing.md](testing.md#empirical-and-formal-verification). *Checked*: a second agent
fetched the page and found the quote; *Read*: one agent fetched it.
- Dijkstra, [EWD303](https://www.cs.utexas.edu/~EWD/transcriptions/EWD03xx/EWD303.html):
  testing shows "the presence of bugs but never ... their absence"; for a black box, "testing
  is the only thing we can do". *Checked.*
- Clarke and Wing, [Formal Methods: State of the Art and Future Directions](https://www.cs.cmu.edu/~wing/publications/ClarkeWing96.pdf),
  ACM Computing Surveys 1996: definitions; model checking as "exhaustive state space search";
  formal methods do "not a priori guarantee correctness". *Read.*
- Newcombe et al., [Use of Formal Methods at Amazon Web Services](https://lamport.azurewebsites.net/tla/formal-methods-amazon.pdf),
  2014 (CACM 2015): TLA+ on small critical designs, because "testing the code is inadequate
  as a method to find subtle errors in design". *Read.*
- Jackson, [Alloy](https://groups.csail.mit.edu/sdg/pubs/2019/alloy-cacm-18-feb-22-2019.pdf),
  CACM 2019: bounded checking within a scope; the small scope hypothesis. *Read.*
- [CrossHair](https://crosshair.readthedocs.io/en/latest/limitations.html): symbolic execution
  of Python contracts; "the absence of a counterexample does not guarantee that the property
  holds". *Checked.*
- [z3py `prove()`](https://z3prover.github.io/api/html/namespacez3py.html): proves a claim "by
  showing the negation is unsatisfiable". *Read.*
- Lamport, [TLA+ tools](https://lamport.azurewebsites.net/tla/tools.html): TLC, "an
  explicit-state model checker" for safety and liveness. *Read.*
- Kleppmann, [AI will make formal verification go mainstream](https://martin.kleppmann.com/2025/12/08/ai-formal-verification.html),
  2025: with proofs automated, the hard part becomes "correctly defining the specification".
  *Checked.*
- Bursuc et al., [A benchmark for vericoding](https://arxiv.org/abs/2509.22908), 2025:
  off-the-shelf LLMs met given formal specifications 27% in Lean, 44% in Verus, 82% in Dafny.
  *Read.*

## RTS test reference (2026-11-03)

[DeepMind PySC2](https://github.com/google-deepmind/pysc2), inspected at
`0df53d38c153972f1e368572ba65b1442a0fd41f`:
[mock_sc2_env_test.py](https://github.com/google-deepmind/pysc2/blob/0df53d38c153972f1e368572ba65b1442a0fd41f/pysc2/env/mock_sc2_env_test.py)
tests episode transitions, including two episodes on one environment;
[protocol_error_test.py](https://github.com/google-deepmind/pysc2/blob/0df53d38c153972f1e368572ba65b1442a0fd41f/pysc2/tests/protocol_error_test.py)
checks specific protocol/request errors and replay behaviour against the actual SC2 process.
Read as a research-code reference for WH3 transition tests and the separation between fake
environment tests and live-engine evidence. Neither its tests nor SC2 ran here; its stepping
model is not WH3's unpaused 1x timing contract. Application and evidence: [testing review](testing.md#mailbox-transition-review-2026-11-03).

## Robot coordination reference (2026-11-04)

Mandi, Jain and Song, [RoCo](https://doi.org/10.1109/ICRA57147.2024.10610855), ICRA 2024:
**RoCoBench** tests robot cooperation through task dependencies, different capabilities
and shared space. The [overview](twwarhammer3/benchmark-references/rocobench.md) maps these
to WH3 unit-group owners and allied army owners, with timing limits and pinned code.
The [cooperation display proposal](twwarhammer3/benchmark-references.md#make-cooperation-inspectable-before-scoring-it)
also uses `task_cabinet.py` (continuing support) and `prompting/display_utils.py` (attributed
decisions beside execution) at the overview's pin. Independent source audit:
`runs/cooperation-evidence/source-audit.md`. No experiment reproduced.
Black, Galliker and Levine, [Real-Time Chunking](https://arxiv.org/abs/2506.07339v2),
NeurIPS 2025: condition new plans on execution during inference; continuous-action inpainting
is not directly applicable to WH3 orders. Used as an execution principle in that proposal.
Literature reference only; no experiment or verification method adopted.

## Cross-domain research reference (2026-11-02)

Karttunen et al., [From Video Game to Real Robot: The Transfer Between Action Spaces](https://doi.org/10.1109/ICASSP40776.2020.9053221),
ICASSP 2020. [Research summary](thesis/papers.md#cross-domain-test-design-from-video-game-to-real-robot):
experimental design, evidence limits and possible WH3 comparisons for later discussion.
Literature reference only; no experiment or verification method adopted.

## WH3 benchmark reference profiles

For the [scenario guidelines](twwarhammer3/scenario-guidelines.md), added 2026-11-04:
- Ribeiro et al., [CheckList](https://aclanthology.org/2020.acl-main.442/) (ACL 2020),
  section 2: capability matrices, minimum functionality, invariance and directional tests.
  The WH3 adaptation must establish its own behavioral expectations and equivalences.
- Cobbe et al., [Procgen](https://arxiv.org/abs/1912.01588) (ICML 2020): procedural
  variation and evaluation on unseen instances. It does not establish WH3 generator
  validity or select our sample counts. Source audit: `runs/scenario-guidelines/research-audit.md`.

The [Boris scenario source register](twwarhammer3/boris-scenarios-sources.md) records SEGA's
DLC-only ownership rules, CA unit/patch descriptions and competitive-context sources,
with exact excerpts and access limits. It supports the
[battle proposals](twwarhammer3/boris-scenarios.md), not live verification or adoption.

The [WH3 tactics source register](twwarhammer3/tactics-sources.md) collects historical
accounts from NPS, the National Army Museum and English Heritage, plus CA mechanics guides
and patch notes. It supports the [tactics catalogue](twwarhammer3/tactics-reference.md) and
[candidate evaluations](twwarhammer3/tactics-evaluation.md); game effects remain unverified.

The [reference index](twwarhammer3/benchmark-references.md) and its profiles collect
task-construction methods, evaluation semantics and pinned implementation entry points.

- [BEHAVIOR](https://github.com/StanfordVL/BEHAVIOR-1K): household task definitions,
  starting states and goal checks; [profile](twwarhammer3/benchmark-references/behavior.md).
- [CARLA Leaderboard](https://github.com/carla-simulator/leaderboard) and
  [ScenarioRunner](https://github.com/carla-simulator/scenario_runner): traffic situations,
  event criteria and versioned scores; [profile](twwarhammer3/benchmark-references/carla.md).
- [SMACv2](https://github.com/oxwhirl/smacv2): generated tactical situations, partial
  observation and coordination; [profile](twwarhammer3/benchmark-references/smacv2.md).
- Zhu et al., [MultiAgentBench (ACL 2025)](https://aclanthology.org/2025.acl-long.421/),
  [MARBLE code](https://github.com/ulab-uiuc/MARBLE): LLM team structures, communication
  and separate task/coordination measures; complements SMACv2 for our split-army comparison.
  [Profile](twwarhammer3/benchmark-references/multiagentbench.md) includes pinned code,
  WH3 connections and limits of its scheduling, judge scores and disabled graph metrics.

Source inspection dated 2026-11-01; MultiAgentBench added 2026-11-02. Exact revisions and
primary papers are in the profiles.
No external benchmark results reproduced or WH3 verification established by these sources.

## GaP graph controllers for WH3 (2026-10-31)

- Chen et al., [GaP paper v1](https://arxiv.org/html/2607.05369v1), July 2026:
  the method motivating our proposed WH3 extension, not evidence of battle performance.
- [Graph-as-Policy](https://github.com/graph-robots/graph-as-policy), inspected at
  `71549e1584839337eb355c280e7b1e50c805b8c7`: `gap/agent/multi_agent.py`,
  `gap/runtime/{workflow,validate,executor}.py`, `gap/benchmark/__init__.py`,
  `tests/agent/test_pipeline.py`, `tests/runtime/test_executor.py`; references for
  authoring, graph contracts and independent tests. Its benchmark describes one-shot
  generation, not the paper's full rehearsal loop. No external tests were run.
- [GaP docs](https://graph-robots.github.io/graph-as-policy/): workflow schema,
  executor semantics, skill authoring and postcondition checks. Their “checkpoints” are
  verification predicates, not WH3 replay restoration.
- [Open Robot Skills](https://github.com/graph-robots/open-robot-skills), inspected at
  `752dfbd96968d4d08379f8111765efbf6457800b`: `skills/transporting-objects/SKILL.md`
  supplies a concrete catalog pattern, not transferable battle tactics.

The [WH3 GaP plan](twwarhammer3/gap-plan.md#references) links each donor file and explains
what to mirror or change. Research entry: [papers](thesis/papers.md#gap-graph-as-policy-for-variational-automation).
Code/docs inspection only; no robotics results reproduced or WH3 GaP behavior verified.

## Anthropic provider (2026-10-31)

Live Anthropic docs behind `gameai/providers.py` `ANTHROPIC` and the Messages translation in
`gameai/llm.py` ([plan](anthropic-provider-plan.md)). "Checked" here: the planning agents
read the page and the implementing session re-fetched it on 2026-10-31 for the facts used.
- [Versioning](https://platform.claude.com/docs/en/api/versioning): `2026-10-21` is the
  latest; for Messages it only refuses `temperature`/`top_p`/`top_k` and two citation and
  document shapes. *Checked.*
- [Authentication](https://platform.claude.com/docs/en/manage-claude/authentication):
  `Authorization: Bearer` (`x-api-key` legacy); a key not scoped to a workspace must send
  `anthropic-workspace-id` on every request, else HTTP 400. *Checked.*
- [Messages reference](https://platform.claude.com/docs/en/api/messages/create): request
  `output_config` {effort, format} and `thinking` {adaptive, display}; reply `stop_reason`
  values and `usage`, whose `input_tokens` excludes cache reads and writes and whose
  `output_tokens_details.thinking_tokens` is part of `output_tokens`. *Checked.*
- [Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs):
  `output_config.format = {type: json_schema, schema}`; limits of 16 union-typed and 24
  optional parameters; enum capitalization not guaranteed; grammars cached 24 h. *Checked.*
- [Errors](https://platform.claude.com/docs/en/api/errors) and
  [rate limits](https://platform.claude.com/docs/en/api/rate-limits): 529 overloaded; an
  organization or workspace spend limit you set returns 400; the tier spend cap returns 429
  `enforced_spend_limit_reached`; a per-key budget is not documented there. *Checked*
  (rate limits: *read*).
- [Pricing](https://platform.claude.com/docs/en/about-claude/pricing): Haiku 5.5 $0.10 /
  $0.01 / $0.50 per M input / cache-read / output tokens up to 100,000 prompt tokens (five
  times above), Sonnet 5.5 $2 / $0.10 / $10, Opus 5.5 $4 / $0.20 / $20. *Checked.*
- [Effort](https://platform.claude.com/docs/en/build-with-claude/effort),
  [thinking](https://platform.claude.com/docs/en/build-with-claude/thinking),
  [prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
  (opt-in), [refusals and fallbacks](https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback),
  [Models API](https://platform.claude.com/docs/en/api/models/retrieve). *Read.*
- [Claude Code and `ANTHROPIC_API_KEY`](https://code.claude.com/docs/en/iam): why the repo
  reads only `GAMEAI_ANTHROPIC_*` variables. *Read.*
- [Commercial Terms](https://www.anthropic.com/legal/commercial-terms) §D.4 and the
  [Usage Policy](https://www.anthropic.com/legal/aup) (effective 2026-11-12): no training of
  competing models; no training on outputs ("model scraping" or "model distillation")
  without prior authorization. *Checked* (the rerun reviewer re-fetched both, 2026-10-31).

Each entry ends with its status:
- **checked**: a second agent re-fetched the page and confirmed the quotes or facts we use;
- **read**: one agent read it; not re-checked;
- **secondary**: someone else's summary (a recap or a listing), not the author's own words;
- **unread**: the page could not be fetched.

Collected 2026-10-28 and 2026-10-29 for the light factory plan, now [workflow.md](workflow.md).
Vendor pages (Sonar) are marketing: use their terms, not their numbers.

## Agent context loading

Read 2026-11-02 for the [workflow reading routes](workflow.md#start-here):

- OpenAI, [Rethinking skills and prompts for GPT-6 Astra](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra),
  2026-09-11: task-specific document pointers and progressive disclosure reduce irrelevant
  context. This supports routing guidance; it does not measure this repository's token use.
- OpenAI, [Codex Prompting Guide](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide#using-agentsmd):
  `AGENTS.md` is injected from the global and root-to-working-directory instruction chain.
  Inference from that mechanism: linked pages still need an explicit read.
- OpenAI, [Hooks](https://learn.chatgpt.com/docs/hooks#tool-coverage): `exec_command` matches
  `Bash`; project hooks need trust for the current definition. The repo's native refusal
  probe is recorded in [workflow.md](workflow.md#claude-code-and-codex); Stop is still unverified.

Gate isolation, read 2026-11-02: Hugging Face Hub
[`src/huggingface_hub/file_download.py`](https://github.com/huggingface/huggingface_hub/blob/main/src/huggingface_hub/file_download.py)
serializes shared cache writes with `WeakFileLock`. Our Unix-only gate uses
[`fcntl.flock`](https://docs.python.org/3/library/fcntl.html#fcntl.flock) on a persistent
file for the same ownership pattern; it does not adopt Hub's download logic or dependencies.

## WH3 native multiplayer assessment

Checked 2026-10-30 for the [feasibility draft](twwarhammer3/native-multiplayer.md).
Installed CA documentation and bridge source were independently audited; cost sources and
arithmetic were independently checked. No live multiplayer or cloud performance result.

- [SEGA WH3 FAQ](https://support.sega.com/hc/en-gb/articles/4417717186833-TOTAL-WAR-WARHAMMER-III-FAQ):
  advertised 2–8-player battles; not proof of scripted multiplayer control.
- CA-authored scripting references, community mirrors:
  [battle](https://chadvandy.github.io/tw_modding_resources/WH3/battle/battle.html),
  [unitcontrollers](https://chadvandy.github.io/tw_modding_resources/WH3/battle/battle_unitcontroller.html),
  [unit HP and morale API](https://chadvandy.github.io/tw_modding_resources/WH3/battle/battle_unit.html#function:unit:unary_hitpoints)
  (`unary_hitpoints` measures regiment HP relative to initial HP; used by mirror-v1),
  [timers](https://chadvandy.github.io/tw_modding_resources/WH3/battle/timer_manager.html),
  [UI synchronization warning](https://chadvandy.github.io/tw_modding_resources/WH3/ui_scripting.html).
  Installed copies under `runs/twwarhammer3/vanilla/` govern this build.
- [Steam matchmaking](https://partner.steamgames.com/doc/features/multiplayer/matchmaking):
  lobby discovery/join primitives, not evidence WH3 exposes them to Lua.
- [Steam WH3 US store](https://store.steampowered.com/app/1142710/Total_War_WARHAMMER_III/?cc=us&l=english)
  and [Steam Account Use](https://help.steampowered.com/en/faqs/view/71EA-CDCE-FB5C-82B3):
  base-game price, Windows storage and separate concurrent accounts/licenses.
  Corrected on refinement: the prior 48C1 link described routers, not licensing.
- AWS [Windows workstation cost example](https://docs.aws.amazon.com/solutions/latest/modular-cloud-studio-on-aws/cost.html),
  [G4 hardware](https://aws.amazon.com/ec2/instance-types/g4/),
  [graphics drivers](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/nvidia-GRID-driver.html),
  [gp3 storage](https://aws.amazon.com/ebs/volume-types/),
  [IPv4 pricing](https://aws.amazon.com/vpc/pricing/): approximate infrastructure costs;
  the workstation rate is a published example, not a live EC2 quote.
- [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing): illustrative
  input/output costs, not a choice of game policy or evidence of provider access or latency.
- Farama-Foundation/PettingZoo
  [`pettingzoo/test/parallel_test.py`](https://github.com/Farama-Foundation/PettingZoo/blob/main/pettingzoo/test/parallel_test.py):
  per-agent identity and episode-lifecycle checks. Inspected, not run; its synchronous
  stepping contract does not establish real-time multiplayer synchronization.

Refinement, 2026-10-30: independent cloud, reference/headless/RL and source reviews;
evidence in `runs/twwarhammer3/multiplayer-plan-20261030/`. Sources inspected, no deployment
or external project execution. Proposed checks remain unagreed.

- Google Cloud [Windows GPU workstation](https://docs.cloud.google.com/compute/docs/virtual-workstation/windows-gpu),
  [vWS drivers](https://docs.cloud.google.com/compute/docs/gpus/install-grid-drivers),
  [G2 restrictions](https://docs.cloud.google.com/compute/docs/accelerator-optimized-machines),
  [nested virtualization](https://docs.cloud.google.com/compute/docs/instances/nested-virtualization/overview),
  [IAP access](https://docs.cloud.google.com/iap/docs/using-tcp-forwarding),
  [runtime limits](https://docs.cloud.google.com/compute/docs/instances/limit-vm-runtime),
  [`gcloud compute instances create`](https://docs.cloud.google.com/sdk/gcloud/reference/compute/instances/create),
  [budget limitations](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps):
  candidate Windows Server/vWS setup and lifecycle constraints, not WH3 support or a quote.
- airgpu [pricing](https://airgpu.com/),
  [billing](https://help.airgpu.com/guides/how-billing-works/index.html),
  [Windows licensing](https://help.airgpu.com/guides/windows-licensing/index.html),
  [Moonlight setup](https://help.airgpu.com/getting-started/connect-to-your-machine/index.html),
  [no WSL2](https://help.airgpu.com/common-issues/nested-virtualization/index.html):
  public headline rates and setup; worker access/unattended automation not established.
- Primary implementation reference: [PySC2](https://github.com/google-deepmind/pysc2),
  `0df53d38c153972f1e368572ba65b1442a0fd41f`,
  [`sc2_env.py`](https://github.com/google-deepmind/pysc2/blob/0df53d38c153972f1e368572ba65b1442a0fd41f/pysc2/env/sc2_env.py)
  and [`multi_player_test.py`](https://github.com/google-deepmind/pysc2/blob/0df53d38c153972f1e368572ba65b1442a0fd41f/pysc2/tests/multi_player_test.py):
  separate real client processes, create/join, identity and cleanup. README and open issues
  368/369 inspected; no Windows/version compatibility result reproduced. SC2 API/headless
  support and synchronous stepping do not transfer to WH3.
- Secondary orchestration reference: [AI Arena match controller](https://github.com/aiarena/sc2-ai-match-controller),
  `b5f6c9b36c2bc36b1914287f876a7da7b65d1ada`, component READMEs,
  [`game_result.rs`](https://github.com/aiarena/sc2-ai-match-controller/blob/b5f6c9b36c2bc36b1914287f876a7da7b65d1ada/sc2_controller/src/game/game_result.rs)
  and [issue 165](https://github.com/aiarena/sc2-ai-match-controller/issues/165):
  preparation/finalization and result reconciliation; no adoption of its container stack,
  future game-agnostic API or timeout-as-loss rules.
- Tinker [Env](https://tinker-docs.thinkingmachines.ai/cookbook/api-reference/rl/env/)
  and [EnvGroupBuilder](https://tinker-docs.thinkingmachines.ai/cookbook/api-reference/rl/envgroupbuilder/);
  Prime Intellect [Verifiers v1](https://docs.primeintellect.ai/verifiers/v1/overview),
  [Env](https://docs.primeintellect.ai/verifiers/v1/env),
  [harnesses](https://docs.primeintellect.ai/verifiers/v1/harnesses): possible later RL adapters,
  not established Windows game hosting, native reset or a training decision.
- [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve) and
  [Microsoft WSL networking](https://learn.microsoft.com/en-us/windows/wsl/networking):
  proposed private HTTPS worker link and Windows-to-WSL localhost backend. Docs establish
  those primitives, not compatibility with the selected cloud PC or an approved account.

Implementation, 2026-10-30 (merged at `5d10e2a`; [status](twwarhammer3/native-multiplayer.md#implementation-status)):

- PySC2 [`run_configs/platforms.py`](https://github.com/google-deepmind/pysc2/blob/0df53d38c153972f1e368572ba65b1442a0fd41f/pysc2/run_configs/platforms.py)
  at `0df53d38`: install paths chosen per platform; followed by `gameai/windows.py`. **read**
  (2026-10-30, during the doc check)
- Python [`msvcrt.locking`](https://docs.python.org/3/library/msvcrt.html#msvcrt.locking) and
  Microsoft [`LockFileEx`](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-lockfileex):
  the native lock, unlocked before close because the time Windows takes to release a lock on
  close depends on available system resources (LockFileEx remarks). **read** (2026-10-30,
  during the doc check)
- Kubernetes client-go [`tools/leaderelection/leaderelection.go`](https://github.com/kubernetes/client-go/blob/4563439f729012b84179286a88bc9d191bf3d35e/tools/leaderelection/leaderelection.go)
  at `4563439f`: a client acts only on times from its own clock, and a holder that cannot renew
  within RenewDeadline calls OnStoppedLeading once; client-go stamps its observed time after the
  update returns, while `engine/link.py` times the worker lease from the send time. **read**
- Public list prices for the quote worksheet (`runs/twwarhammer3/native-multiplayer/quote-worksheet.md`,
  git-ignored; not a quote): Google Cloud
  [GPU regions](https://docs.cloud.google.com/compute/docs/gpus/gpu-regions-zones),
  [accelerator-optimized pricing](https://cloud.google.com/products/compute/pricing/accelerator-optimized),
  [disk pricing](https://cloud.google.com/compute/disks-image-pricing),
  [network pricing](https://cloud.google.com/vpc/network-pricing);
  [airgpu](https://airgpu.com/); [Tailscale pricing](https://tailscale.com/pricing). **checked**
- Valve [Steam browser protocol](https://developer.valvesoftware.com/wiki/Steam_browser_protocol):
  `steam://joinlobby/<appid>/<lobby id>/<steam id>`; cited from memory in
  `twwarhammer3/mp-next-steps.md` (step 1 join routes). **unread**
- Microsoft [CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew):
  `FILE_SHARE_DELETE` lets another handle delete or rename an open file; behaviour
  measured on Windows 11 for `mp-next-steps.md` step 2, Server 2022 untested. **unread**
- Steam [ISteamMatchmaking](https://partner.steamgames.com/doc/api/ISteamMatchmaking):
  friends-only lobbies do not show up in the lobby list; on an accepted invite Steam posts
  GameLobbyJoinRequested_t if the game is running, else launches it with `+connect_lobby <id>`.
  Acting on either is the game's own code; whether WH3 does is unknown. Used by the static
  lobby audit (`runs/twwarhammer3/native-multiplayer/lobby-static-audit.md`, git-ignored).
  **checked**

## WH3 multiplayer control foundation

Read 2026-11-03 for the [control foundation plan](twwarhammer3/multiplayer-control-foundation.md).
Sources support the integration approach, not a working WH3 native binding:

- CA [UI scripting](https://chadvandy.github.io/tw_modding_resources/WH3/ui_scripting.html),
  community mirror: UI-triggered model mutations may desynchronize multiplayer. Installed
  build 26403568 layouts were read in memory for actual readiness/host/join callback bindings.
- Valve [ISteamMatchmaking](https://partner.steamgames.com/doc/api/ISteamMatchmaking):
  create/join and asynchronous lobby callbacks. These do not establish WH3 session setup.
- [Frida JavaScript API](https://frida.re/docs/javascript-api/): native interception/calls,
  the reentrancy warning on `Process.runOnThread`, and batching/overhead guidance. Correct
  game-thread execution points and native signatures still require engine-specific checks.
- PySC2 [multiplayer test](https://github.com/google-deepmind/pysc2/blob/0df53d38c153972f1e368572ba65b1442a0fd41f/pysc2/tests/multi_player_test.py),
  pin `0df53d38c153972f1e368572ba65b1442a0fd41f`: explicit create/join/player identity,
  repeated matches and cleanup. WH3 must remain live at 1x; its implementation cannot copy
  SC2's synchronized stepping or assume an official/headless engine API.

## VM team plan (2026-11-03)

Outside sources for the [VM team plan](twwarhammer3/vm-team-plan.md), read by research and
review agents on 2026-11-03 (web only; nothing created or run).

- [WH3 EULA](https://store.steampowered.com/eula/1142710_eula_1) §7(b), (c), (e), (f): one
  computer at a time; no "remote access arrangement"; no reverse engineering, decompiling or
  modifying; no circumventing "security protections". **checked** (by a review agent)
- [Boris Todbringer store page](https://store.steampowered.com/app/3589670/): grants Immortal
  Empires; multiplayer for a DLC-only account not mentioned. **checked**
- [Steam thread 4302697675601825934](https://steamcommunity.com/app/1142710/discussions/0/4302697675601825934/)
  (2024): compare `modified` logs; a movie-type mod in `data/`, mod versions or game versions
  explain the remaining "incompatible" joins. **secondary**
- [IAP TCP forwarding](https://docs.cloud.google.com/iap/docs/using-tcp-forwarding): idle
  connections close after 1 h. **secondary**
- [NVIDIA vGPU known issue 3583766](https://docs.nvidia.com/vgpu/20.0/known-issues/bug-3583766-multiple-rdp-reconnections-use-all-frame-buffer.html):
  repeated RDP reconnects on Server 2022 use up GPU frame buffer. **checked**

## GCP client setup guide (2026-11-02)

Sources for the [Google Cloud setup guide](twwarhammer3/gcp-client-setup.md), read by two
research agents on 2026-11-02 (web only; nothing created or run); a third agent rechecked the
guide's claims against them and its 16 findings were applied. Official pages **checked**;
forum posts and third-party sites **secondary**.

- Google Cloud: [free-trial limits](https://docs.cloud.google.com/free/docs/free-cloud-features),
  [GPU quota names](https://docs.cloud.google.com/compute/resource-usage),
  [quota requests](https://docs.cloud.google.com/sdk/gcloud/reference/quotas/preferences/create),
  [quota IDs](https://docs.cloud.google.com/sdk/gcloud/reference/quotas/info/list),
  [gcloud quota examples](https://docs.cloud.google.com/docs/quotas/gcloud-cli-examples),
  [quota review](https://docs.cloud.google.com/docs/quotas/overview),
  [G2 zones](https://docs.cloud.google.com/compute/docs/gpus/gpu-regions-zones),
  [G-series VMs](https://docs.cloud.google.com/compute/docs/gpus/create-gpu-vm-g-series),
  [Windows images](https://docs.cloud.google.com/compute/docs/images/os-details),
  [Windows SSH (Preview)](https://docs.cloud.google.com/compute/docs/connect/windows-ssh),
  [Windows startup scripts](https://docs.cloud.google.com/compute/docs/instances/startup-scripts/windows),
  [Windows passwords](https://docs.cloud.google.com/sdk/gcloud/reference/compute/reset-windows-password),
  [vWS licence](https://docs.cloud.google.com/compute/docs/gpus/about-gpus),
  [GPU host maintenance](https://docs.cloud.google.com/compute/docs/gpus/gpu-host-maintenance),
  [virtual display device](https://docs.cloud.google.com/compute/docs/instances/enable-instance-virtual-display),
  [stockouts](https://docs.cloud.google.com/compute/docs/troubleshooting/troubleshooting-resource-availability),
  [stopping VMs from a budget](https://docs.cloud.google.com/billing/docs/how-to/control-usage):
  account, quota, VM and lifetime facts; forum reports of automatic GPU quota refusals:
  [2024-12](https://discuss.google.dev/t/gpu-quota-increase-beyond-0/176297),
  [2026-07](https://discuss.google.dev/t/blocked-by-automated-gpu-quota-denials-on-academic-research-grant/377219).
- NVIDIA [RDS sessions skip the GPU on Windows Server](https://docs.nvidia.com/vgpu/19.0/known-issues/bug-no-id-no-gpu-utilization-windows-server-guests.html),
  [licensed display limits](https://docs.nvidia.com/vgpu/latest/grid-licensing-user-guide/intro-to-grid-licensing.html);
  Microsoft [RDS hardware-GPU policy](https://learn.microsoft.com/en-us/windows/client-management/mdm/policy-csp-admx-terminalserver),
  [auto-logon](https://learn.microsoft.com/en-us/troubleshoot/windows-server/user-profiles-and-logon/turn-on-automatic-logon),
  [Sysinternals Autologon](https://learn.microsoft.com/en-us/sysinternals/downloads/autologon),
  [scheduled-task principals](https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtaskprincipal):
  what makes a game render on a Server VM; none of it is a WH3 result.
- Valve [SteamCMD](https://developer.valvesoftware.com/wiki/SteamCMD) and
  [Steam command line](https://developer.valvesoftware.com/wiki/Command_Line_Options_(Steam));
  [WH3 store page](https://store.steampowered.com/app/1142710/) (Windows 7/10, 120 GB);
  us-east1 machine price from [gcloud-compute.com](https://gcloud-compute.com/g2-standard-4.html) (third-party).
- Reference repos for the in-VM steps: [gcloudrig](https://github.com/gcloudrig/gcloudrig)
  (`gcloudrig.psm1`, `gcloudrig-boot.ps1`; T4 vWS on Compute Engine with Steam; last push
  2023-11) and [Parsec Cloud Preparation Tool](https://github.com/parsec-cloud/Parsec-Cloud-Preparation-Tool)
  (`PostInstall/PostInstall.ps1`; archived 2025-10, Server 2016/2019). Fallback display driver:
  [parsec-vdd](https://github.com/nomi-san/parsec-vdd). Read, not run.
- Forum reports that a disconnected RDP session stops drawing:
  [Classmethod](https://dev.classmethod.jp/articles/parsec_host_black_screen_when_rdp_disconnected),
  [SmartBear](https://support.smartbear.com/testcomplete/docs/ver-14-2/testing-with/running/via-rdp/keeping-computer-unlocked.html).

## Cloud usage and cleanup (2026-11-02)

Official sources read for [cloud usage](cloud.md); two live cleanup cases are recorded there:
- [VM runtime limits](https://docs.cloud.google.com/compute/docs/instances/limit-vm-runtime):
  stop clears the termination timestamp; termination can begin up to 30 seconds late.
- [Disk auto-deletion](https://docs.cloud.google.com/compute/docs/disks/modify-persistent-disk#auto-delete):
  `autoDelete=true` removes an attached disk with its VM; retained disks keep billing.
- [Budget alerts](https://docs.cloud.google.com/billing/docs/how-to/budgets) and
  [spend caps](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps):
  billing delay and the eligible services, which exclude Compute Engine.
- Workflows [deadline waiting](https://docs.cloud.google.com/workflows/docs/reference/stdlib/sys/sleep_until),
  [VM deletion](https://docs.cloud.google.com/workflows/docs/reference/googleapis/compute/v1/instances/delete)
  and [pricing](https://cloud.google.com/workflows/pricing): cleanup primitives,
  charged by executed steps. Official docs alone do not establish our implementation's correctness.
- Reference pattern: GoogleCloudPlatform/workflows-demos,
  [long-running-container/prime-generator.yaml](https://github.com/GoogleCloudPlatform/workflows-demos/blob/master/long-running-container/prime-generator.yaml),
  VM deletion from an external workflow; adapted to fixed deadlines and exact target names.
- [Resource availability errors](https://docs.cloud.google.com/compute/docs/troubleshooting/troubleshooting-resource-availability):
  stockouts are separate from quota; trying another zone or later is Google's documented response.
- Region retry implementation: [SkyPilot, sky/provision/provisioner.py](https://github.com/skypilot-org/skypilot/blob/master/sky/provision/provisioner.py),
  `bulk_provision` stops failover if teardown fails. Our runner stops when absence is uncertain.
  Google's [Billing catalogue API](https://docs.cloud.google.com/billing/v1/how-tos/catalog-api)
  supplied the regional SKU rates; live accelerator/machine listings supplied supported zones.
  Eight regional quotes and 22 advertised zones checked on 2026-11-03 UTC, without provisioning;
  evidence: `runs/gcp-region-fallback-20261102/`. Advertised support does not establish capacity.

## Verification talks and Sonar

- [How Anthropic Merges 30,000 Code Changes a Day](https://www.youtube.com/watch?v=AnsXWH2_EBU),
  Manish Kapur (Sonar) and Addy Osmani (Anthropic), AI Engineer New York, October 2026. Sonar's
  pre-event release says Oct 13, the conference schedule says Oct 14; uploaded 2026-10-28. An
  onstage conversation: light vs dark factories, Claude as first-pass reviewer, "why every loop in
  the factory needs independent, multi-layered verification". Listing and chapters only;
  transcript unread. *Secondary.*
- [AI Engineer NY 2026 schedule](https://ai.engineer/nyc/2026/schedule): the same session as "Who
  verifies the software factory?". The abstract quotes CircleCI: 28 million workflows, throughput
  up 59%, nearly three in ten attempts to merge into production fail (not checked against
  CircleCI).
  *Secondary.*
- [StartupHub.ai recap](https://www.startuphub.ai/ai-news/technology/2026/anthropic-now-merges-30-000-changes-a-day),
  Daniel Singer, 2026-10-28. Paraphrases Kapur's three layers: deterministic (bugs, security),
  agentic (logic, intent), supply chain (CVEs, malicious packages). Mixes in material from outside
  the talk. *Secondary; quotes checked.*
- [daily.dev listing](https://daily.dev/posts/how-anthropic-merges-30-000-code-changes-a-day---manish-kapur-sonar-addy-osmani-anthropic-bqbqoutup):
  title and link only. *Secondary.*
- [Sonar at AI Engineer New York](https://www.sonarsource.com/company/press-releases/sonar-at-ai-engineer-new-york/),
  press release, 2026-10-08. Session list, plus the CEO keynote's "code confidence formula":
  intent × guiderails × independent verification × auditable evidence. *Checked.*
- [Code is abundant. Confidence is a formula.](https://dev.to/dailycontext/code-is-abundant-confidence-is-a-formula-gn6),
  Manish Kapur, dev.to, 2026-10-12. Four questions, one of them: "Did something other than the
  model that wrote the change check it?" *Checked.*
- [The reviewer can't be the author](https://www.wearedevelopers.com/videos/100432-the-reviewer-can-t-be-the-author-independent-verification-for-ai-generated-code),
  Manish Kapur, WeAreDevelopers, 2026-09-23. Listing only; the video needs an account.
  *Secondary.*
- [In the Land of AI Agents, the Verifiers Are King](https://ai.engineer/talks/in-the-land-of-ai-agents-the-verifiers-are-king),
  Tariq Shaukat (Sonar's CEO), AI Engineer World's Fair 2026
  ([video](https://www.youtube.com/watch?v=VrpEyglYgeU)). Slide 11:11: "Verification should be
  zero-trust and multilayered". Slide 11:47 lists the algorithmic and agentic layer names the
  plan uses. The page has a transcript and slide text. *Checked.*
- [Guide, Verify, Solve](https://ai.engineer/talks/guide-verify-solve-the-engineering-discipline-agentic-development-demands),
  Anirban Chatterjee (Sonar), same event. Verification "needs to run in both the inner agentic
  loop and also in the outer loop". *Checked.*
- [What is zero-trust verification in software delivery?](https://www.sonarsource.com/resources/library/zero-trust-verification-in-software-delivery/),
  Brooks Naylor, Sonar, 2026-09-29. Six layers. The critical failure is "using the same method that
  wrote the code to verify it"; "Findings from later layers must flow back to earlier ones".
  *Checked.*
- [Deterministic vs probabilistic code analysis](https://www.sonarsource.com/resources/library/deterministic-vs-probabilistic-code-analysis/),
  Brooks Naylor, Sonar, 2026-10-15. A deterministic baseline is the gate; LLM review is a signal.
  *Checked.*
- Sonar's agent-centric development cycle:
  - [Verify page](https://www.sonarsource.com/agent-centric-development/verify/): verify inside the
    agent's loop and again "at sandbox exit before the PR opens".
  - [overview](https://www.sonarsource.com/agent-centric-development/): a background
    code-maintenance loop.
  - [docs](https://docs.sonarsource.com/agent-centric-development-cycle/): "Each loop feeds the
    next".

  *Checked.*
- [SonarQube World Tour New York](https://www.sonarsource.com/events/world-tour/new-york-city/),
  event page, 2026-10-15. Three loops: agentic, CI verification, code remediation. Its statistics
  give no method. *Checked.*
- Sonar blog and survey pages:
  - [collective action on cyber defense](https://www.sonarsource.com/blog/sonar-supports-openai-call-for-collective-action-on-cyber-defense/)
    (Rob Taylor, 2026-09-14): where the "zero-trust, multilayered" and "three loops" wording
    appears.
  - [Skyscanner's AI rollout](https://www.sonarsource.com/blog/what-skyscanners-ai-rollout-proves-about-verifying-ai-generated-code/)
    (2026-09-25).
  - [State of Code survey is open](https://www.sonarsource.com/blog/the-next-state-of-code-developer-survey-is-open/)
    (2026-09-08).
  - [Verification gap](https://www.sonarsource.com/company/press-releases/sonar-data-reveals-critical-verification-gap-in-ai-coding/)
    (2026-01-08): only 48% of developers always verify AI output before committing.

  *Checked* (quotes and the 48%; the other posts' dates are *read*).
- [State of Code 2027 teaser](https://www.sonarsource.com/resources/state-of-code-developer-survey-2027/):
  "AI writes 65% of committed code, but 76% of developers can't verify it fast enough". No method
  or sample size. *Checked.*

## Software factories

- [Software Factories, Light and Dark](https://addyosmani.com/blog/software-factories/), Addy
  Osmani, 2026-07-20. Defines light ("run the loop with humans in it") and dark factories. "You can
  only hand a loop as much autonomy as you can cheaply and reliably verify." A loop can run alone
  only if its check is cheap, frequent and hard to fake. *Checked.*
- [Human judgment doesn't leave the software factory](https://addyosmani.com/blog/human-judgment-doesnt-leave-the-software/),
  Addy Osmani, 2026-08-21 (X version:
  [Do you need a software factory?](https://x.com/addyosmani/status/2092865809299476767),
  2026-08-27). "You can get surprisingly far with your stock coding harness". A factory pays off
  for repeatable runs, hand-offs, claim locks, kept evidence and pausing when review falls behind.
  Its first section gives a minimal factory prompt. *Checked.*
- [Own the Outer Loop](https://addyo.substack.com/p/own-the-outer-loop), Addy Osmani, 2026-07-09.
  "An independent check, not the model's own say-so, decides when the work is done." *Read.*
- [The Code Nobody Reads](https://addyo.substack.com/p/the-code-nobody-reads), Addy Osmani,
  2026-09-28. Advice for one developer: write what you're building, what it must not break and how
  you'll know it worked; say what you didn't review. *Checked.*
- [Agentic Verification](https://addyo.substack.com/p/agentic-verification), Addy Osmani,
  2026-10-14. Less "review every line", more "build loops the agent can run itself". *Checked.*
- [Software Factories And The Agentic Moment](https://factory.strongdm.ai/), StrongDM (Justin
  McCarthy), 2026-02-06. No human writes or reviews code. Scenarios are held out like a test set
  because "Tests can be reward hacked". *Checked.*
- [How StrongDM's AI team build serious software without even looking at the code](https://simonwillison.net/2026/feb/7/software-factory/),
  Simon Willison, 2026-02-07. Doubts about skipping review, and the cost. *Checked.*
- [The Five Levels](https://www.danshapiro.com/blog/2026/01/the-five-levels-from-spicy-autocomplete-to-the-software-factory/),
  Dan Shapiro, 2026-01-23. Level 5 is the dark factory. *Checked.*
- [Agency and agents](https://www.oneusefulthing.org/p/agency-and-agents), Ethan Mollick,
  2026-08-31. A "Twilight Factory" where agents reach out to people. *Read.*
- [Software factories](https://codingscape.com/blog/software-factories-how-ai-agents-ship-code-start-to-finish),
  Codingscape, undated marketing. "Light factory – agents write most of the code, and a human reads
  it before it ships." *Read.*
- [Harness engineering for coding agent users](https://martinfowler.com/articles/harness-engineering.html),
  Birgitta Böckeler, 2026-04-02. Guides steer before the agent acts; sensors check after. Each is
  computational (tests, linters) or inferential (AI review). *Checked.*
- Thoughtworks Technology Radar, Vol. 34, 2026-04-15. *Checked.*
  - [Feedback sensors for coding agents](https://www.thoughtworks.com/radar/techniques/feedback-sensors-for-coding-agents),
    at Trial: run checks during the session, before a commit.
  - [Agent instruction bloat](https://www.thoughtworks.com/radar/techniques/agent-instruction-bloat),
    at Caution: as rule files grow, important rules are more likely to be ignored.
  - [Mutation testing](https://www.thoughtworks.com/radar/techniques/mutation-testing), at Trial:
    "high coverage percentages can mask logically hollow tests".
- [DORA 2025 report](https://dora.dev/research/2025/dora-report/): "AI's primary role is as an
  amplifier". See also its
  [capabilities model post](https://cloud.google.com/blog/products/ai-machine-learning/from-adoption-to-impact-putting-the-dora-ai-capabilities-model-to-work/)
  (2025-12-09). *Checked.* Its [working in small batches](https://dora.dev/capabilities/working-in-small-batches/)
  page is *read*.
- [Advanced context engineering for coding agents](https://github.com/humanlayer/advanced-context-engineering-for-coding-agents/blob/main/ace-fca.md),
  HumanLayer, about August 2025. Research, plan, implement. Reviewing the plan gives more leverage
  than reviewing the code. *Read.*

## Claude Code and Anthropic

Claude Code docs (undated; read 2026-10-28):
- [Best practices](https://code.claude.com/docs/en/best-practices). It covers:
  - instructions the model reads vs rules the harness enforces;
  - give Claude a check to run and ask for its output;
  - review against the spec ("A reviewer that's asked to find problems will always find
    something");
  - five questions before a run goes unattended.

  *Checked.*
- [Hooks](https://code.claude.com/docs/en/hooks) and the [hooks guide](https://code.claude.com/docs/en/hooks-guide):
  only exit 2 (or a JSON decision) blocks; `onFailure`; an end-of-turn hook is overridden after
  eight blocks in a row with no tool call between them. *Checked.*
- [Memory](https://code.claude.com/docs/en/memory): aim for "under 200 lines per CLAUDE.md file";
  imports don't reduce context cost; AGENTS.md is read only when no CLAUDE.md exists. *Checked.*
- [/goal](https://code.claude.com/docs/en/goal): a small fast model judges "met" from the
  transcript, without running tools. *Checked.*
- [Permission modes](https://code.claude.com/docs/en/permission-modes): limits stated in chat are
  only classifier signals; use deny rules for hard limits. *Checked.*
- [Skills](https://code.claude.com/docs/en/skills): loaded from `.claude/skills`; symlinked skill
  folders work. *Checked.*
- [Workflows](https://code.claude.com/docs/en/workflows): rerunnable fan-out scripts;
  `/deep-research` lists claims its verifiers can't check as unverified. *Checked.*
- [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices):
  don't hard-code to make tests pass; report wrong tests. *Checked.*

Anthropic posts:
- [Redesigning source control](https://www.anthropic.com/research/redesigning-source-control),
  2026-10-13. Covers:
  - 2,500 to over 30,000 merges a day (May to September);
  - review of intent rather than every line;
  - adversarial review that over-engineers;
  - a token budget that "far exceeds what any other business would realistically want to spend".

  *Checked.*
- [How the Claude Code team does code review](https://claude.dev/blog/solving-code-review-at-anthropic/),
  Addy Osmani, Morgan Westlee Lunt and Qing Wang, 2026-10-15 (X rewrite 2026-10-26). It covers the
  Claude Code repo, not the monorepo:
  - evidence before the pull request;
  - risk tiers ("The change sets the tier, not the author");
  - a soft three-round cap, after which the author rethinks the approach;
  - past incidents as the reviewer's eval;
  - reverts and incidents as the guardrail;
  - an adoption checklist.

  *Checked.*
- [Harness design for long-running application development](https://www.anthropic.com/research/harness-design-long-running-apps),
  2026-03-24. A separate evaluator tuned to be skeptical; a contract for "done" before code; drop
  steps after model upgrades. *Checked.*
- [Effective harnesses for long-running agents](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents),
  2025-11-26. Progress file plus git, one feature per session, a basic test before new work.
  *Checked.*
- [Demystifying evals for AI agents](https://www.anthropic.com/research/demystifying-evals-for-ai-agents),
  2026-01-09. With frontier models, 0% across many trials usually means a broken task. Covers
  reference solutions and an "Unknown" answer for LLM judges. *Checked.*
- [Building a C compiler with parallel Claudes](https://www.anthropic.com/research/building-c-compiler),
  2026-02-05. The verifier must be nearly perfect; keep test output terse. *Checked.*
- [How AI agents shape experts' judgment calls](https://www.anthropic.com/research/agents-judgment-calls),
  2026-10-27. Analysts took the agent's lean 86% of the time. *Checked.*
- [Long-running Claude for scientific computing](https://www.anthropic.com/research/long-running-claude),
  2026-03-23. Needs a way to know progress (a test oracle); progress file. *Read.*
- [How we contain Claude](https://www.anthropic.com/research/how-we-contain-claude), 2026-05-25.
  Hard limits at the environment first; approval fatigue undermines oversight. *Read.*
- [Investigating unintended model actions](https://www.anthropic.com/research/investigating-unintended-model-actions),
  2026-10-09. Models working around restrictions; a model's account of its reasons isn't reliable
  evidence. *Read.*

## Codex and OpenAI

Codex docs (now at learn.chatgpt.com; undated; read 2026-10-28):
- [Best practices](https://learn.chatgpt.com/guides/best-practices): goal, context, constraints,
  "done when"; a retrospective after the same mistake twice; don't schedule a task before it works
  by hand. *Checked.*
- [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md): files read from the
  repo root down to the working directory, up to 32 KiB combined by default. *Checked.*
- [Hooks](https://learn.chatgpt.com/docs/hooks): "a useful guardrail, not a complete enforcement
  boundary"; exit 2 blocks before tool calls; end-of-turn hooks that exit 0 print JSON; project
  hooks need a trusted `.codex/`. *Checked.* Read again 2026-10-29 for the Codex hooks: the
  `Bash` matcher covers shell commands and `exec_command`; exit 0 with no output is success;
  `Stop` accepts `systemMessage`; each hook is trusted with `/hooks` by its hash, so a changed
  one is skipped until trusted again. *Read.*
- [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents): one TOML file per
  custom agent in `.codex/agents/`, with `name`, `description` and `developer_instructions`;
  sandbox and approvals come from the parent session; a prompt names the agent to spawn it.
  Used for `.codex/agents/reviewer.toml` (2026-10-29). *Read.*
- [Rules](https://learn.chatgpt.com/docs/agent-configuration/rules): experimental command rules for
  commands outside the sandbox. *Read.*
- [Build skills](https://learn.chatgpt.com/docs/build-skills): loaded from `.agents/skills`;
  symlinks followed. *Checked.*
- [Long-running work](https://learn.chatgpt.com/docs/long-running-work): `/goal`; a goal grants no
  extra access. *Checked.*
- [Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode.md): `codex exec`,
  read-only sandbox by default, `--output-schema`. *Checked.*
- [Auto-review](https://learn.chatgpt.com/docs/sandboxing/auto-review.md): "a reviewer swap, not a
  permission grant". *Checked.*
- [Agent approvals & security](https://learn.chatgpt.com/docs/agent-approvals-security): sandbox
  modes; `approval_policy = "untrusted"` is retired. *Checked.*
- [Review GitHub pull requests](https://learn.chatgpt.com/docs/third-party/github): a
  `## Code Review Rules` section; GitHub reviews flag only P0 and P1 issues. *Read.*
- [Config sample](https://learn.chatgpt.com/docs/config-file/config-sample.md): `review_model` for
  `/review`. *Read.*

OpenAI posts and cookbook:
- [Custom Code Review rules for Codex](https://developers.openai.com/blog/custom-code-review-rules-for-codex):
  write two or three rules for non-obvious invariants; test each with one triggering change, one
  safe change and one unrelated change. *Checked.*
- [Rethinking skills and prompts for GPT-6 Astra](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra):
  short skill descriptions. Its advice to drop forced testing conflicts with our rules. *Checked.*
- [Run long horizon tasks with Codex](https://developers.openai.com/blog/run-long-horizon-tasks-with-codex):
  milestones with acceptance criteria and validation commands; repair before moving on. *Read.*
- [Iterating development workflows with Codex](https://developers.openai.com/cookbook/examples/codex/iterating-development-workflows-with-codex):
  "Never claim that a test ... passed unless it was actually run"; a phase stays In progress or
  Blocked without evidence. *Checked.*
- [Using PLANS.md for multi-hour problem solving](https://developers.openai.com/cookbook/articles/codex_exec_plans)
  (archived): ExecPlans with Progress, Surprises & Discoveries, Decision Log, Outcomes &
  Retrospective. *Checked.*
- [Using Goals in Codex](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex):
  the model may mark a goal complete "only when the evidence supports completion". *Checked.*
- [Harness engineering](https://openai.com/index/harness-engineering/): the original returned 403.
  A [repost](https://gitcode.csdn.net/69ef655d0a2f6a37c5a6667a.html) (2026-04-27) has these points:
  - AGENTS.md as a roughly 100-line map;
  - custom lints whose messages say how to fix the problem;
  - doc gardening.

  Byline and date unverified. *Unread original; repost checked.*
- [Codex orchestration (Symphony)](https://openai.com/index/open-source-codex-orchestration-symphony/):
  returned 403. *Unread.*
- [codex-plugin-cc](https://github.com/openai/codex-plugin-cc): Codex's `/codex:review` and
  `/codex:adversarial-review` inside Claude Code; uses Codex quota. *Read.*

## Diagram viewers

For [how-code-works.html](how-code-works.html) (then `multi-agent.html`), the animated diagram of the multi-agent parts
(2026-10-31). We copy techniques, not code; the viewer names each source in a comment.
Checked on 2026-10-31 by a second agent (`runs/multi-agent-diagram-20261031/maps-and-references.json`).

- [architecture-diagram-skill](https://github.com/konraddzbik/architecture-diagram-skill)
  (`skills/architecture-diagram/assets/template.html`, MIT): a flow is a list of steps with from,
  to, title and payload; wires are quadratic curves (:1564); play, pause and step keys. Its
  packets ride SMIL `<animateMotion>` (:1640) and only one wire is lit at a time; we place each
  dot per frame with `getPointAtLength`, which it uses to rest a packet at a wire's end (:1687).
  *Checked.*
- [RaftScope](https://github.com/ongardie/raftscope) (`script.js`, ISC-style): several messages
  in flight on one clock, each at (now - sendTime) / (recvTime - sendTime) of its path
  (:450-453); a time slider that pauses and seeks (:736-756). *Checked.*
- [Dask dashboard task stream](https://docs.dask.org/en/stable/dashboard.html) (BSD-3): "Each row
  represents a thread, and each rectangle represents an individual task"; white space is idle
  time. The lanes under the canvas follow it. *Checked.*
- [Archify](https://github.com/tt-a1i/archify) (Apache-2.0): claims cite sources pinned to a
  commit (README:88); Timeline and Waterfall specs mark their evidence "illustrative" or
  measured (README:286-287), as each flow here does. *Checked.* Links that restore a view and
  motion that respects `prefers-reduced-motion` (README:434). *Read.*
- [The Secret Lives of Data: Raft](http://thesecretlivesofdata.com/raft/) (MIT): captioned frames,
  one short caption per step. *Checked.*

Looked at and not used: [GitDiagram](https://github.com/ahmedkhaleel2004/gitdiagram) and
[PR Lens](https://github.com/coldteadotai/pr-lens) send the repository or each diff to a model
provider; [React Flow](https://reactflow.dev/examples/edges/animating-edges) needs React;
[Mermaid](https://mermaid.js.org/syntax/flowchart.html) animates edges by moving dashes;
[Dashmotion](https://github.com/csthink/dashmotion) also moves dashes, and on this
page dashes mean "planned". *Checked.*

## How the code works page (2026-11-01)

For the [plan](how-code-works-plan.md) that turns `multi-agent.html` into a whole-repo map plus
short stories. Each quote was checked against a saved copy on 2026-11-01
(`runs/diagram-upkeep-plan-20261031/pass2/`, `python3 -I pass2/verify_quotes.py
pass2/quotes.json`: every quote found, 0 missing). *Checked* means those quotes only, not the
whole source.

- [C4 model](https://c4model.com/), Simon Brown: "maps of your code" at "various levels of
  detail"; large diagrams overload the reader; "each diagram will change at a different rate".
  The map-then-stories split and the idea that areas change rarely follow it. *Checked.*
- Bret Victor, [Up and Down the Ladder of Abstraction](https://worrydream.com/LadderOfAbstraction/)
  (2011) and [Explorable Explanations](https://worrydream.com/ExplorableExplanations/) (2011):
  move between levels; "an explorable example makes the abstract concrete". *Checked.*
- [Diátaxis](https://diataxis.fr/explanation/), Daniele Procida: an explanation answers a "why"
  question; explanation tends to absorb other material. Each story's title is its question.
  *Checked.*
- matklad, [ARCHITECTURE.md](https://matklad.github.io/2021/02/06/ARCHITECTURE.md.html) (2021):
  a codemap answers "where's the thing that does X?" and names only what rarely changes. The
  one-file-per-line lists follow it. *Checked.*
- *Software Engineering at Google*, [ch. 10](https://abseil.io/resources/swe-book/html/ch10.html)
  (Tom Manshreck): accuracy can give way to clarity; "freshness dates" with reminders after
  three months. The 92-day review flag follows it. *Checked.*
- [The Secret Lives of Data: Raft](https://thesecretlivesofdata.com/raft/): one small scenario,
  one plain sentence per step; raft.github.io calls it "more guided and less interactive".
  The story player follows it. *Checked.*
- Weinstein, Madan and Sumeracki (2018), [Teaching the science of
  learning](https://pmc.ncbi.nlm.nih.gov/articles/PMC5780548/): concrete examples help
  understanding; LeFevre and Dixon (1986), as it reports: when examples and instructions
  disagreed, students followed the examples. So examples are copied by script. *Checked*
  (the review only; LeFevre and Dixon *secondary*).

## GitHub Actions

For `.github/workflows/check.yml` (2026-10-29):

- [Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use):
  "Pin references to actions to a commit SHA in your workflow files"; give the `GITHUB_TOKEN`
  read access to contents only. *Read.*
- [setup-uv](https://github.com/astral-sh/setup-uv) `action.yml` at v10.2.0: the `version` input
  pins uv. Releases and tag commits were read through the GitHub API. *Read.*

## Specs

- [Kiro feature specs](https://kiro.dev/docs/specs/feature-specs/) and
  [correctness](https://kiro.dev/docs/specs/correctness/), updated 2026-08-04. EARS requirements
  ("WHEN … THE SYSTEM SHALL …") and property-based tests; "not formal verification". *Checked.*
- [GitHub Spec Kit](https://github.com/github/spec-kit): a command pipeline from spec to code; many
  markdown files. *Checked.*
- [Understanding spec-driven development: Kiro, spec-kit and Tessl](https://www.martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html),
  Birgitta Böckeler, 2025-10-15. Spec-first, spec-anchored and spec-as-source. Kiro turned one
  small bug into 16 acceptance criteria. *Checked.*
- [Spec-driven development](https://www.thoughtworks.com/radar/techniques/spec-driven-development),
  Thoughtworks Radar, 2025-11-05, at Assess. Elaborate workflows and long specs. *Checked.*
- [Tessl](https://tessl.io/): now calls itself an "agent enablement platform". *Read.*

## Testing, evaluation and research code

- [Recent Frontier Models Are Reward Hacking](https://metr.org/blog/2025-06-05-recent-reward-hacking/),
  METR, 2025-06-05. Models edit tests and scoring code. Fix the scorer rather than penalising
  through a monitor. *Checked.*
- [Frontier Risk Report](https://metr.org/blog/2026-05-19-frontier-risk-report/), METR,
  2026-05-19. Reward hacking persisted with hidden tests; one attempt failed only because scoring
  ran in its own container (INC-031). *Checked.*
- [Algorithmic vs holistic evaluation](https://metr.org/blog/2025-08-12-research-update-towards-reconciling-slowdown-with-time-horizons/),
  METR, 2025-08-12. Agent PRs passed tests on 38% of tasks, but none of the 15 reviewed PRs was
  mergeable as-is. *Read.*
- [Agentic Benchmark Checklist](https://arxiv.org/html/2507.02825v5), Zhu, Kang et al., 2025.
  Outcome and task validity; trivial-agent baselines. Already cited in the
  [evaluation guidelines](twwarhammer3/evaluation-guidelines.md). *Checked.*
- [Gymnasium env_checker](https://gymnasium.farama.org/_modules/gymnasium/utils/env_checker/)
  ([v1.4.0 source](https://raw.githubusercontent.com/Farama-Foundation/Gymnasium/v1.4.0/gymnasium/utils/env_checker.py)).
  Seeded resets must match and observations must be fresh objects. The
  [passive checker](https://gymnasium.farama.org/api/wrappers/misc_wrappers/) checks only the first
  calls. *Checked.*
- [PettingZoo environment tests](https://pettingzoo.farama.org/content/environment_tests/): API,
  seed and max-cycles tests for multi-agent environments. *Checked.*
- [CleanRL](https://jmlr.org/papers/v23/21-1342.html), Huang et al., JMLR 2022. Single-file RL
  implementations, benchmarked. *Checked.*
- [Hypothesis stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html): random
  sequences of operations checked against a simple model. *Checked.*
- [mutmut](https://mutmut.readthedocs.io/en/latest/): plants small bugs and reports those no test
  catches; needs fork (WSL is fine). [Cosmic Ray](https://cosmic-ray.readthedocs.io/en/latest/)
  is an alternative we skip. *Checked.*
- [Import Linter](https://import-linter.readthedocs.io/en/stable/): enforces import contracts
  between packages. A small `ast` test does the same without a dependency. *Checked.*
- [Inspect eval logs](https://inspect.aisi.org.uk/eval-logs.html) and
  [API reference](https://inspect.aisi.org.uk/reference/inspect_ai.log.html), UK AISI. Check a
  log's status before using its results; edits are appended with author and reason. *Checked.*
- [SWE-bench run report](https://github.com/SWE-bench/SWE-bench/blob/02e7a74ffd0b/swebench/harness/reporting.py)
  (`make_run_report`, `schema_version` 2). Each instance gets one label from its evidence:
  resolved, unresolved, error, empty patch or incomplete; failure-cause tags are added without
  changing the denominator. The model for `cards.benchmark_outcome` (2026-10-31). *Read.*
- [NeurIPS paper checklist](https://neurips.cc/public/guides/PaperChecklist): claims match their
  scope; error bars say what varies and how they were computed; failed experiments count in
  compute. *Checked.*
- [Pre-registration workshop](https://neurips.cc/virtual/2020/workshop/16158), NeurIPS 2020. The
  protocol is reviewed before results exist. *Checked.*
- [How SQLite is tested](https://sqlite.org/testing.html#mutation_testing): mutation testing and
  deliberately broken builds. *Checked.*
- [Deep RL at the Edge of the Statistical Precipice](https://arxiv.org/abs/2108.13264), Agarwal et
  al. Interval estimates for few-run RL comparisons. Already cited in
  [benchmark-implementation.md](twwarhammer3/benchmark-implementation.md). *Read.*
- [Empirical Design in Reinforcement Learning](https://jmlr.org/papers/v25/23-0183.html), Patterson
  et al., JMLR 2024. Designing RL experiments: variation, baselines, hyperparameters, experimenter
  bias. *Read.*
- [Lessons from the Trenches on Reproducible Evaluation of Language Models](https://arxiv.org/abs/2405.14782),
  Biderman et al. Share exact prompts and outputs; read a small batch before scaling up. *Read.*
- [Leakage and the Reproducibility Crisis in ML-based Science](https://arxiv.org/abs/2207.07048),
  Kapoor and Narayanan. Eight kinds of data leakage across 329 papers. *Read.*
- [Good enough practices in scientific computing](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1005510),
  Wilson et al., PLOS Computational Biology, 2017. A minimal set of habits for one researcher.
  *Read.*
- [CPython `Tools/patchcheck/patchcheck.py`](https://github.com/python/cpython/blob/main/Tools/patchcheck/patchcheck.py)
  (fetched 2026-10-29). One command reports what a change touched, measured against its base
  branch (`git diff --name-status <base>`, else `git status`); the model for `scripts/check.py`'s
  base and warnings. *Read.*
- pytest-dev/pytest [`src/_pytest/junitxml.py`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/junitxml.py),
  `LogXML.pytest_sessionfinish`: the session-finish hook writes the JUnit report. Read in
  installed pytest 9.1.1 on 2026-10-31 for the normal gate's completion evidence; an abrupt
  zero exit can leave no report. Local source and subprocess examples inspected; no claim
  that XML alone proves full collection or correctness. *Read.*
- [transformers `Makefile`](https://github.com/huggingface/transformers/blob/main/Makefile) and
  [`utils/check_repo.py`](https://github.com/huggingface/transformers/blob/main/utils/check_repo.py)
  (fetched 2026-10-29). `make check-repository-consistency` runs repository rules as plain checks
  in CI; the model for `tests/test_repo_rules.py`. Makefile targets read; check_repo.py skimmed.
  *Read.*
- [GitHub CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners):
  named files need a named reviewer; the idea behind `check.py`'s "needs your yes" for agreed
  checks' files. Cited from memory, page not fetched. *Unread.*
- Hugging Face datasets [`tests/test_fingerprint.py`](https://github.com/huggingface/datasets/blob/main/tests/test_fingerprint.py),
  `HashingTest.test_hash_simple` (read 2026-10-31): identical inputs repeat their identity,
  changed inputs do not. Pattern for the source-provenance byte-change test; our SHA-256
  expectations use independent input bytes, with size and timestamps held fixed. *Read.*
- Hugging Face datasets [`tests/utils.py`](https://github.com/huggingface/datasets/blob/main/tests/utils.py)
  (read 2026-10-31): shared test helpers live outside collected test modules. Pattern for
  `tests/combat/combat_support.py` and the evidence/catalog and language/PPO support modules, preserving
  helper logic while imports and module qualifiers change.
  Its `offline()` context also illustrates isolating an external boundary while running
  real code, used for the hook cleanup test's child-interpreter process scan. *Read.*
- PyTorch [`.github/workflows/lint.yml`](https://github.com/pytorch/pytorch/blob/main/.github/workflows/lint.yml),
  `test_collect_env` (read 2026-10-31): separate matrix entries exercise environments with
  different installed dependencies. Pattern for the optional-extra jobs in our check workflow;
  their CPU execution does not establish CUDA behavior. *Read.*
- actionlint [`docs/install.md`](https://github.com/rhysd/actionlint/blob/v1.7.12/docs/install.md):
  Go installation command inspected on 2026-10-31; task-local v1.7.12 validates workflow
  syntax and action expressions. Shellcheck was unavailable; profile shell commands run directly.


### Launcher failure contract tests (2026-10-31)

Pattern: Farama-Foundation/Gymnasium [`tests/vector/test_async_vector_env.py`](https://github.com/Farama-Foundation/Gymnasium/blob/main/tests/vector/test_async_vector_env.py), `test_async_vector_subenv_error`: inject a controlled worker failure and check the caller-visible error and shutdown diagnostics. Read Git blob `8042a56332fd4b641b568ec864e79e84d919cb2b`; snapshot under `runs/test-quality-20261031/audit-worktree/audit-stop-contract/`. This audit uses fake restore calls; Gymnasium's async-worker tests were not reproduced.

- [FFmpeg gfxcapture documentation](https://ffmpeg.org/ffmpeg-filters.html#gfxcapture)
  (read 2026-11-04): native-window selection, D3D11 download and duplicate frames for the
  support-timing manual recorder. Local live capture is unverified.
