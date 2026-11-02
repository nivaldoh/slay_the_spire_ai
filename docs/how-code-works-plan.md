# Plan: a visual "how the code works" page that stays true

Second version, 2026-11-01, Claude Code, at `d12be58`. Nothing is built. The first version, which treated
keeping file:line claims accurate as the goal, and the checkers' evidence are in
`runs/diagram-upkeep-plan-20261031/` (local, not in Git).

**The owner's answers (2026-11-01):** "My answers: 1a, 2a, 3a. About the three questions that need my
'yes', I agree with them." So:
- the page becomes a "How the code works" map plus short stories;
- refreshes run as away-window upkeep or on request, at most weekly, at most 100 API calls each;
- small battle excerpts are committed in `docs/` (public);
- the three changes to the 2026-10-31 build answers are approved.

The defaults below were not answered one by one; they stand as the agent's choices and get `JUDGEMENT?:`
markers where they are built. Approval is not verification.

The owner (2026-11-01): "the general idea of helping me quickly understand how the code works in a visual,
concrete, simple, intuitive way. That's by far the most important thing". The owner (2026-10-31): it should
be "the main way I understand the structure of our codebase and execution of the code", stay current as part
of the factory, and not be updated after every commit.

Understanding comes first. Freshness matters because a wrong picture teaches the wrong thing.

## Decisions (answered 2026-11-01: 1a, 2a, 3a)

**1. What should the page be?**
- **(a, recommended) A "How the code works" map of the whole repo, plus short picture stories built on
  real battles.** Today's five tabs stay as a frozen appendix: three known-wrong boxes are fixed, and each
  tab is removed once a story replaces it.
- (b) As (a), but keep maintaining all five tabs, claim by claim. At `1fd6811` the first plan's recheck
  list already held 173 items for them.
- (c) Keep the WH3 multi-agent scope and only make today's tabs simpler.

Example: GaP's graph controllers, the active track (4 new files, 849 lines, added today), appear nowhere on
the page. Under (a) they get a map box, "Graph controllers: run a battle as a graph of steps", and their graph
files can be drawn by a script. Best case for (c): the smallest change, keeping what you have already seen.

**2. When does a refresh run, and what may it cost?**
Today nothing triggers one.
- **(a, recommended) In an away window as standing upkeep work, or when you ask; at most once a week.**
  - A script lists the flagged views for free.
  - One refresh may use at most 100 API calls. One build tab review used 58-102.
  - A refresh that would exceed the cap stops and reports instead.
- (b) Only when you ask.
- (c) A refresh of everything every week, whether flagged or not.

Example: since `21f6204` (about one day, 62 commits), 7 of the 28 code files the page cites changed, and so
did the provider list. Under (a), that would be one refresh within the week. Before you fix the cadence, the
pilot replays the last three weeks of commits through the flagging script, at no token cost, and reports how
many views each week would have flagged. Best case for (b): no surprise spending at all.

**3. Where do the examples come from?**
- **(a, recommended) A script copies small excerpts of recorded battles into committed files in `docs/`.**
  - Each excerpt names its job and commit.
  - Excerpts become public on GitHub (the repo is public), including the model's prompt and reasoning text.
  - This is a standing exception to "run evidence stays out of Git", for small excerpts only.
  - The merged replay file `docs/multi-agent-replay.js` (31 KB) already works this way. You have not yet
    approved it (build handoff question 2).
- (b) The script writes the excerpts under the ignored `runs/`, and the page loads them from there. Nothing
  new enters Git or goes public, but the examples are missing in worktrees and on other machines, and are
  lost with `runs/`, which has no backup.
- (c) Hand-written examples labelled "made up".

Example: the "One decision" story would show what the model sent (shortened), its order
`{"unit":"f2","type":"move","x":-380,"z":40,"run":true}`, with its reason "f2 got dragged into melee with e3
... pulling it out west". Best case for (b): the evidence rule stays intact and nothing goes public.

**Also pending: changes to your build answers of 2026-10-31.** This plan changes three of them; each needs
your yes:
- "No drift test (your choice)" and "no new tests". The plan adds a flagging script to `check.py`, with 2-3
  small tests of the script itself.
- "Planned parts faded and dashed, with a switch to hide them". The plan hides planned parts by default.
- "Every box … shows its status". The plan moves status colours behind a "How sure is this?" switch, and
  colour then shows what a part does.

**Defaults I would follow unless you say otherwise:**
1. One reviewer rechecks every claim in each refreshed view, keeping your 10-31 rule. The checking method
   stays unagreed. Build handoff question 4 is still yours; this default recommends leaving it unagreed.
2. A story has at most 12 boxes and 8 steps, with captions of at most 20 words. The reviewer checks these
   limits.
3. No game time is spent just for the page. Examples come from battles that ran anyway, so a story whose
   code changed keeps its badge "code changed since" until a new battle runs.
   - Alternative: one scripted, $0 battle per away window.
4. Every view gets a full review at least every 3 months. This catches quiet views and claims about things
   outside Git, such as GitHub settings and provider APIs.
5. "Never ran in the game" is a status set by hand, citing its evidence, and checked at each refresh.
   `results.csv` alone would be wrong: the scripted team passed its live check without writing rows there.
6. The understanding quiz (section 4) is tried once in the pilot and made standing only on your yes. Its
   pass marks are 4 of 5 with pictures and at most 2 of 5 without.
7. The pilot stops if your look says it does not help, or if it costs more than one build tab did (a draft
   of 96-145 API calls plus a review of 58-102). We then fall back to 1(c).

**Still open from the build handoff:**
- Q1, the look: this plan changes it.
- Q2, the merged replay: see decision 3.
- Q3, the multiplayer `link.py` close() race: unrelated, still open. Recommended: a one-line check plus a test.
- Q4: see default 1.

## Today's page, seen as a reader

From the page at `d12be58`. Counts are tab totals; a single flow draws fewer, e.g. the default Play loop
picture has 14 boxes.

| Tab | Boxes | Wires | Steps | Real example? |
|---|---|---|---|---|
| Overview | 9 | 8 | 8 | No; all 8 steps loop at once, so it shows no order |
| Play loop | 23 | 32 | 55 | One real battle, told in side-panel text; the picture shows a dot |
| Team | 18 | 26 | 133 (3 flows; longest 64) | A real scripted probe; its timeline of the two members is the clearest picture on the page |
| Multiplayer | 21 | 39 | 47 | No; no multiplayer battle has run |
| Factory | 23 | 37 | 36 | No; a star of arrows around one box |

What helps:
- the coloured bands showing where each part runs;
- the moving dots;
- the Team timeline.

What hurts:
- **Too much at once.** Pictures of 14-23 boxes, and flows of up to 64 steps.
- **Code names instead of words.** 18 of 23 Play loop box labels are code names, and 16 of the 18
  captions in its "One decision" flow use ids such as `r24`.
- **The explanation is buried.** The current step's sentence sits below method notes in the side panel,
  and about a third of the panel's text is file references.
- **Colour means "how sure", not "what it does".**
- **It covers only WH3 battles.** It cites 28 of the 120 source files under `src/` and `scripts/`, and none
  of Spire's 44. GaP, checkpoints, reports and post-training have no box.
- **Some of it is wrong now.** Three boxes say the model provider is "OpenAI or OpenRouter", but
  `providers.py` also lists Anthropic.

## The plan

### 1. What the page becomes

One page, still `docs/multi-agent.html` so links keep working, retitled "How the code works". Three levels
(owner, 2026-11-01: now `docs/how-code-works.html`, "How the WH3 code works", its map without Slay
the Spire):

1. **A map of the whole repo, the first view.** About 12 area boxes in today's coloured bands:
   - the WH3 play loop and controllers;
   - GaP graphs;
   - scenarios and setup;
   - the game runtime;
   - checkpoints and RL;
   - reports and stats;
   - model calls and budget;
   - multiplayer;
   - Spire;
   - post-training;
   - the factory.

   Each box gives one plain sentence, the command that starts it, a status word (runs today / built, never
   run / paused) and its stories. Clicking a box lists its files. That list is generated from the WH3
   README's existing "Code map", so the repo keeps one home for "which file does what". The flagging script
   reports source files missing from the Code map, and files that belong to no map box. Spire and `gameai` get the same kind of list.
2. **Short picture stories.**
   - Each answers one question, which is its title.
   - At most 8 steps, at most 12 boxes, one thing moving at a time.
   - The current step's sentence sits large, beside the picture.
   - A small box beside the picture shows the actual message at that step, taken from a real recorded
     battle.

   First stories:
   - "What happens in one play job?": command → launch → custom battle with named units → a few decisions
     → result → `results.csv` row → report;
   - "What does the model see and send at one decision?";
   - "Two members, one army", which keeps the Team timeline.

   GaP comes next. Its two graph files (a start step plus named steps, each pointing to the next by
   outcome) can be drawn by script, so the picture stays current while Codex keeps changing them.
3. **Sources, behind a switch:** file references, full status, measurement notes, and which battle an
   example came from.

### 2. Rules for every view

What "simple, concrete, intuitive" means in practice:
- One question as the title, and one sentence of takeaway.
- At most 12 boxes and 8 steps. Every drawn wire has a label. Wires the story does not use are hidden.
- Captions: one sentence of at most 20 words, in plain words. "The Knights (f2)" and "request 24", never
  `r24` alone.
- Labels: the plain name first, the code name small underneath ("Play loop" over `play.py _drive`).
- Every story rests on one named recorded battle. A made-up example says "made up".
- A battle story shows the battle: a small top-down map of the units at the current step.
- Rules the code keeps are stated where they apply: "a policy never sees enemies its side cannot see";
  "the battle never waits for the model".
- Colour shows place and role. Planned parts are hidden by default.
- Text stays readable on a 1366×768 laptop screen, and the caption is visible without scrolling.
- Line numbers appear only in references, never in captions or notes.

### 3. Real examples, made by script

When examples and text disagree, readers follow the examples (LeFevre and Dixon 1986, cited in Weinstein et
al. 2018). So examples are copied from recorded battles by a script, never typed. For example, "One
decision" uses `bench-b45-knights3-glm-low-l1-20261020`, in which GLM 5.3 commands our Swordsmen and Empire
Knights against three Swordsmen:
- what the model saw at 79.7 s, from `twwarhammer3 digest <episode> --at 80`;
- its reply (trace row 99), shown in section "Decisions (answered 2026-11-01: 1a, 2a, 3a)", question 3;
- the order applied at 83.0 s, a repeat of the move applied at 79.7 s;
- the map of the Knights running west, drawn from the episode's `replay.jsonl`.

The script writes plain `.js` data files, because the page opens from disk and cannot fetch other files.
Refreshes rebuild them and commit them with the refresh. The script reads `runs/` from the main checkout,
read-only. An example is flagged "code changed since" only when a file the story itself cites has changed
since that battle, not when any file in the job changed. The latter would flag almost everything: 36 of the
57 files the knights3 job recorded have changed since.

### 4. Does a view teach?

The owner's top criterion, tried once in the pilot:
- Two fresh agents with no repo access answer the same 5 multiple-choice questions about a view. One sees
  screenshots of it; the other sees nothing.
- The view passes if the first scores 4 or more and the second 2 or fewer. A high score without pictures
  means the questions only test general knowledge.
- Example question: "The Knights' order reached the game at 83.0 s. The state the model decided from was
  from (a) 83.0 s, the battle waits; (b) 79.7 s, the battle kept running; (c) 0 s; (d) the model watches
  live." Answer: (b).
- The pilot runs it on today's Play loop tab and on the new story, and reports both scores and the cost.

An agent is not you; your reading decides. "I got lost at step N" becomes a harder question.

### 5. What you see about trust

Shown only when it applies:
- an "out of date" line on a view the script has flagged;
- a striped fill and "never ran in the game" on parts with no live run;
- a badge on each example: "real battle, 20 Oct" (plus "code changed since" when flagged) or "made up".

Everything else sits behind a "How sure is this?" switch. The page says "reviewed by an agent", never
"verified".

### 6. How it stays true without updates after every commit

Different parts go stale at different speeds (C4 model, References). The map's areas change rarely,
generated parts rebuild themselves at each refresh, and an agent only touches the small hand-written parts.

**Flagging** runs inside `check.py`. It uses no agent and prints one console line after the first five, such
as "diagram: 2 views flagged, see the log". The details go to the log and to an ignored data file that the
page reads. It flags:
- a story whose cited code changed. Lines that only moved are updated by matching their text.
- source files missing from the README Code map, or listed there but in no map box. GaP's four new files
  are in the Code map but have no box on today's page, so they would have been flagged.
- examples whose own cited files changed since their battle.
- a few facts read straight from the code: the provider list (which would have caught the three wrong
  boxes) and the hidden observation keys.
- views not reviewed in 3 months.

It skips, with one line saying so, what it cannot do: in CI (no old commits in its shallow copy) and in
worktrees (no `runs/`). Only a run in the main checkout counts.

**Refreshing** follows decision 2:
- one fresh agent in a worktree branch, merged when done, never while a WH3 queue runs;
- it reads one view's data file, not the whole 326 KiB page;
- the scripts rebuild the generated parts;
- one reviewer rechecks every claim in each refreshed view;
- the commit message reports what was checked, what was wrong and the API calls used.

**Cost.**
- Flagging costs one console line.
- A view of 12 boxes and 8 steps should hold about 30-40 claims. The build's reviewers checked 599 claims
  over steps 1-4, 101-183 per step.
- Steady-state cost is unknown until the pilot's three-week replay and its one measured refresh.

## Order of work after your answers

1. **Pilot, in a worktree:**
   - the map;
   - the "What happens in one play job?" story;
   - the flagging script with 2-3 tests;
   - the three-week replay of flag counts;
   - the understanding quiz on today's Play loop and the new story.

   It counts API calls.
2. **Your look.** You open the worktree's page in your Windows browser from a path I give you. I first
   confirm its data files load from there; that has never been tried. Then a 3-minute task, done on both
   today's tab and the pilot:
   - Where is the model provider chosen?
   - What did the Knights' model see at 79.7 s?
   - Which step writes the `results.csv` row?
3. **Stop or continue** under default 7.
4. **Then:** the GaP graph view, "One decision", "Two members, one army". After the pilot: the
   "Diagram refresh" row in `workflow.md`, and links from `docs/state.md`, the WH3 README and `workflow.md`
   pointing at the map instead of the frozen tabs.
5. **After about five refreshes:** keep, simplify or drop each part, as `workflow.md` asks of every step.

## Known gaps

- **The battle map's drawing code.** The WH3 report's `replay.js` and this page both declare top-level `el`
  and `svg`, so the page cannot load it unchanged. It needs a wrapper, or the map is drawn by a Python
  script.
- **Screenshots for the quiz** need Playwright, which lives in `~/.cache/wh3-playwright`, outside
  `uv.lock`. So the quiz runs only on this machine.
- **What scripts cannot see:**
  - claims made false by code they do not cite;
  - changes outside Git (GitHub settings, provider APIs, the game build).

  Reviews catch these: the 3-month floor, and the reviewer's full read of each refreshed view.
- **The old example.** The knights3 battle ran at harness b45 with `llm_rules` v21; today's code is b52 and
  v22. Its badge will say so.
- **Live behaviour.** The page draws what the code does; it verifies no live behaviour.

## References

Quotes were checked against copies in `runs/diagram-upkeep-plan-20261031/pass2/sources/` (local). To rerun,
from that folder: `python3 -I pass2/verify_quotes.py pass2/quotes.json`.

- [C4 model](https://c4model.com/), Simon Brown.
  - "maps of your code", "at various levels of detail".
  - "large diagrams are usually hard to interpret and comprehend because the cognitive load is too high".
  - "each diagram will change at a different rate".
- Bret Victor, [Up and Down the Ladder of Abstraction](https://worrydream.com/LadderOfAbstraction/)
  (2011): "the most powerful way to gain insight into a system is by moving between levels of abstraction".
- Bret Victor, [Explorable Explanations](https://worrydream.com/ExplorableExplanations/) (2011): "An
  explorable example makes the abstract concrete"; "the author holds up their end of the conversation".
- [Diátaxis](https://diataxis.fr/explanation/), Daniele Procida: "it's useful to have a real or imagined
  why question to serve as a prompt"; "One risk of explanation is that it tends to absorb other things."
- matklad, [ARCHITECTURE.md](https://matklad.github.io/2021/02/06/ARCHITECTURE.md.html) (2021): "The
  codemap should answer 'where's the thing that does X?'"; "only specify things that are unlikely to
  frequently change".
- *Software Engineering at Google*, [ch. 10](https://abseil.io/resources/swe-book/html/ch10.html) (Tom
  Manshreck): "sacrificing some accuracy is acceptable for clarity"; "freshness dates", with reminders after
  "for example, three months".
- [The Secret Lives of Data: Raft](https://thesecretlivesofdata.com/raft/): one small scenario, one plain
  sentence per step. raft.github.io calls it "more guided and less interactive, so it may be a gentler
  starting point".
- Weinstein, Madan and Sumeracki (2018), [Teaching the science of
  learning](https://pmc.ncbi.nlm.nih.gov/articles/PMC5780548/): concrete examples "make the ideas easier to
  understand and remember". It reports LeFevre and Dixon (1986): when examples and instructions disagreed,
  "students followed the concrete examples".

These go in `docs/references.md` with the pilot.
