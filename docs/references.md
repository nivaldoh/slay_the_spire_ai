# References

Outside sources for how we build, check and run things: agent workflow, verification, testing,
evaluation and research-code practice. Thesis related work lives in
[thesis/papers.md](thesis/papers.md); testing examples to imitate are also in
[testing.md](testing.md#references-worth-using). Add a source here when it shapes a plan or a
rule, with one line on what it says.

Each entry ends with its status:
- **checked**: a second agent re-fetched the page and confirmed the quotes or facts we use;
- **read**: one agent read it; not re-checked;
- **secondary**: someone else's summary (a recap or a listing), not the author's own words;
- **unread**: the page could not be fetched.

Collected 2026-10-28 and 2026-10-29 for the light factory plan, now [workflow.md](workflow.md).
Vendor pages (Sonar) are marketing: use their terms, not their numbers.

## WH3 native multiplayer assessment

Checked 2026-10-30 for the [feasibility draft](twwarhammer3/native-multiplayer.md).
Installed CA documentation and bridge source were independently audited; cost sources and
arithmetic were independently checked. No live multiplayer or cloud performance result.

- [SEGA WH3 FAQ](https://support.sega.com/hc/en-gb/articles/4417717186833-TOTAL-WAR-WARHAMMER-III-FAQ):
  advertised 2–8-player battles; not proof of scripted multiplayer control.
- CA-authored scripting references, community mirrors:
  [battle](https://chadvandy.github.io/tw_modding_resources/WH3/battle/battle.html),
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

Implementation, 2026-10-30 (branch `wh3-native-mp`; [status](twwarhammer3/native-multiplayer.md#implementation-status)):

- PySC2 [`run_configs/platforms.py`](https://github.com/google-deepmind/pysc2/blob/0df53d38c153972f1e368572ba65b1442a0fd41f/pysc2/run_configs/platforms.py)
  at `0df53d38`: install paths chosen per platform; followed by `gameai/windows.py`. **read**
- Python [`msvcrt.locking`](https://docs.python.org/3/library/msvcrt.html#msvcrt.locking) and
  Microsoft [`LockFileEx`](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-lockfileex):
  the native lock, unlocked before close because release on close is not timed. **read**
- Kubernetes client-go [`tools/leaderelection/leaderelection.go`](https://github.com/kubernetes/client-go/blob/4563439f729012b84179286a88bc9d191bf3d35e/tools/leaderelection/leaderelection.go)
  at `4563439f`: a holder acts only on its own clock and gives up through one callback;
  `engine/link.py` times the worker lease from the send time instead. **read**
- Public list prices for the quote worksheet (`runs/twwarhammer3/native-multiplayer/quote-worksheet.md`,
  git-ignored; not a quote): Google Cloud
  [GPU regions](https://docs.cloud.google.com/compute/docs/gpus/gpu-regions-zones),
  [accelerator-optimized pricing](https://cloud.google.com/products/compute/pricing/accelerator-optimized),
  [disk pricing](https://cloud.google.com/compute/disks-image-pricing),
  [network pricing](https://cloud.google.com/vpc/network-pricing);
  [airgpu](https://airgpu.com/); [Tailscale pricing](https://tailscale.com/pricing). **checked**
- Steam [ISteamMatchmaking](https://partner.steamgames.com/doc/api/ISteamMatchmaking):
  friends-only lobbies are not listed; Steam passes `+connect_lobby` on an accepted invite and
  the game decides whether to honour it. Used by the static lobby audit
  (`runs/twwarhammer3/native-multiplayer/lobby-static-audit.md`, git-ignored). **checked**

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
- [transformers `Makefile`](https://github.com/huggingface/transformers/blob/main/Makefile) and
  [`utils/check_repo.py`](https://github.com/huggingface/transformers/blob/main/utils/check_repo.py)
  (fetched 2026-10-29). `make check-repository-consistency` runs repository rules as plain checks
  in CI; the model for `tests/test_repo_rules.py`. Makefile targets read; check_repo.py skimmed.
  *Read.*
- [GitHub CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners):
  named files need a named reviewer; the idea behind `check.py`'s "needs your yes" for agreed
  checks' files. Cited from memory, page not fetched. *Unread.*
