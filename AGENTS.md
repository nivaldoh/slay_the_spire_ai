# Repository Guidelines

AI policies for original Windows games from WSL; current focus is Total War: WARHAMMER III
(WH3). Codex loads this file; Claude Code imports it through `CLAUDE.md`. Keep hard rules and
task routes here, at most 200 lines. Details belong in the page they govern.

## Start a goal

- Use the goal's named file or handoff first. Do not reread instructions already in context.
- For current work, search [state.md](docs/state.md)'s **Active work** for the relevant entry,
  then read that track's page and matching state section. For a status question, stop when
  the relevant evidence answers it. Docs, tooling and general research need no unrelated game track.
- Before relying on a handoff's branch, job or completion claim, check Git and the relevant
  live process. Read-only work can stay in main; before editing, use your own worktree below.
- Read [workflow Start here](docs/workflow.md#start-here) for the matching task route, not the
  whole workflow. Search [owner-direction.md](docs/owner-direction.md) for relevant authority;
  read a matching [review-queue](docs/review-queue.md) item before acting on a pending decision.
- Before source, config, test or script work, read the relevant [development](docs/development.md)
  sections: Layout and Coding style and tests; Architecture for game/protocol/policy work;
  Commands before invoking game tools. Before Spire work or shared code affecting it, also
  read [docs/spire/AGENTS.md](docs/spire/AGENTS.md); skip it for WH3-only work.
- Cloud work: [cloud.md](docs/cloud.md). Away work: [autonomy.md](docs/autonomy.md).
  Load skills for their actual task, and linked references only when needed. Search headings
  (`rg -n '^##' file`) and read the relevant range; a link is a route, not an automatic import.

## Verification (hard rule)

The owner's rule (2026-10-18): **if the owner has not explicitly discussed with the
assistant how to verify (repeatably test) whether a feature is correct, assume it might
have issues.** Be careful making claims about, or building on top of, unverified things.

- Passing tests, smoke runs and single battles are evidence, not verification. Say
  "unverified" without an agreed method. Claims carry counts, deciding checks and caveats;
  a summary never says more than its log entry.
- Propose a repeatable check when a feature matters; add it to
  [agreed-checks.md](docs/agreed-checks.md) only after the owner agrees. Verification holds
  only at revisions where that check passed. Test what matters; add no slop tests.
- For each change state observable behaviour and an independent requirement, contract or
  trusted example; normal changes put these in a [card](docs/workflow.md#before-a-change-the-card). A recorded output
  alone is not proof. Choose the cheapest relevant checks; show a bug's regression fails
  before the fix where feasible, and challenge important checks with a plausible wrong version.
- Iterate with focused tests; expand for concrete risk. Before **every commit** run
  `uv run --locked python scripts/check.py`; preserve useful failures. Report passed, failed,
  skipped and unavailable checks and their scope. Offline cases establish no live effect or strength.

## Judgement calls

The owner's rule (2026-10-23): agents execute; the owner decides. A judgement call is a
choice no owner direction made that fixes what a benchmark measures, how something is
verified, what comes next, a design whose alternatives change results or their meaning, or
a parameter with benchmark or plan meaning. An agent that makes or finds one marks it in the
same change at the nearest convenient spot (a comment above the line; a note in the page
that documents a file that cannot carry one): `JUDGEMENT:`, or `JUDGEMENT?:` when unsure it
counts, then in one to three lines what was chosen, who and when, the alternative that would
change results and what rests on it. A marked spot may be wrong: say "rests on JUDGEMENT
<file> <name>" for anything built on it, copy its value nowhere without the marker, and park
what [docs/autonomy.md](docs/autonomy.md) parks; a marker is not permission to decide. Only
the owner removes or weakens a marker (an agent only when quoting the owner's words on that
spot in the commit); approval is not verification. Placement limits, the listing command and
the marking pass: [docs/judgement.md](docs/judgement.md).

## Working habits

- Reduce the owner's attention and manual review work as well as bookkeeping and tokens.
  `docs/state.md` stays status only, about 120 lines; new directions go in `docs/owner-direction.md`.
  Log entries stay about 20 lines: change, counted evidence and what is unverified.
- Use multi-agent workflows only for independent verification, the WH3 loop's review step,
  or when the owner asks. Normal changes use the [reviewer](docs/workflow.md#agent-checks-and-the-reviewer).
- For complicated or ambiguous code (benchmarks, evaluation, environments, infrastructure,
  tests, workflows), follow a well-known research repo and name its repo/file in a comment
  or commit (owner, 2026-10-28). Outside sources go in [references.md](docs/references.md).
- Put task scripts, logs, temporary artifacts, diagnostics and test scratch in ignored `runs/`,
  never the home root or unrelated directories. Inventory old garbage; add no unused artifact,
  scenario or diagnostic.
- Edit tracked files only in your own worktree and branch, never the shared main checkout
  ([how](docs/workflow.md#several-sessions-at-once), owner 2026-11-02). Game jobs stay in main
  (rests on JUDGEMENT? docs/workflow.md Worktree details). Delete both once merged. A running
  WH3 queue stops when its checkout's HEAD moves: commit or merge nothing there meanwhile.
  Never link `.venv` or `runs/` between checkouts. A play job also stops when
  its source scope changes; merge nothing touching that scope while it runs, shared code included.
- When a build differs from its pin, tell the owner; re-pin only with approval.
- When the owner is away, use [autonomy](docs/autonomy.md) and the
  [long-run brief/handoff](docs/workflow.md#long-runs-while-the-owner-is-away). The standing menu
  and small interviews were agreed 2026-10-28; other away rules still need the owner's yes.

## Evidence

- Never run two game controllers at once, even for different games; locks protect one game each.
  WH3 always runs unpaused at 1x, including probes. Restore may rebuild faster before handover
  (owner, 2026-10-25); from handover on, 1x. Only the owner may pause while manually demonstrating
  winnability (2026-11-04), never an agent or policy.
- Exclude hidden game state from policies: friendly units in full, visible enemies and the
  custom-battle roster only; no `evaluation`, `final`, `setup`, replay frames or stills.
  Failure classes and engine-only outcomes: [Architecture](docs/development.md#architecture).
- `src/gameai` never imports a game package. Move code there when a second game would copy it,
  not before; per-game job modules stay per game. [Layout](docs/development.md#layout).
- Evidence stays out of Git ([runs/README.md](runs/README.md)). A job's `--budget-usd` caps its
  selected ledger's total, earlier jobs included. Never move or reset a ledger. Deliberately
  create a missing ledger for a new allowance; a mistyped/worktree path must not start at $0.
  The owner's $50 OpenRouter allowance and the Anthropic key's $200 each cover **both games**;
  leave room for both (`<game> spend --provider P`). The key's own limit error is untested.
- WH3 `play` appends an episode row to `docs/twwarhammer3/results.csv`. Log every version in
  `docs/twwarhammer3/log.md` and commit the register with it. Update state when work starts,
  stops or changes direction; keep counts/history in logs. Record source, configuration,
  engine/mod versions and evaluation output; distinguish infrastructure failures from losses.

## Commits and writing

Use concise imperative commit subjects. The owner authorizes commits and pushes to `main`;
keep changes focused and PRs clear about behaviour, checks and limitations. Never commit
proprietary game files, mod jars, game packs or extracted files, saves, bulky trajectories,
checkpoints, API keys or `*:Zone.Identifier` files.

Write simply and concretely (owner, 2026-10-20); no inflated wording or unexplained terms.
No punchlines in public or owner-voiced text (2026-11-04): connected sentences, no tagline
headings, closers for effect or "X, not Y"; see `runs/portfolio/AGENTS.md`, Writing.
