# Working while the owner is away

What Claude Code and Codex may do alone when the owner cannot review or decide. Proposed
2026-10-21; in force once the owner says yes. [AGENTS.md](../AGENTS.md) still applies in
full. The owner ([2026-10-20](owner-direction.md)) wants progress "without keeping me as a
bottleneck unless critical", first on "features that can be counted as objective, easier to
verify", such as WH3 campaign infrastructure; designing the campaign benchmark stays theirs.

## When it applies

- **Busy**: the owner says they cannot review but may be using the PC. Offline work only.
- **Away**: the owner says they are leaving and gives a return time; the PC is free until
  then, under [game time](#game-time).
- Both end at the return time or at any owner message to either agent. The [limits](#limits)
  are shared by Claude and Codex and reset only after the owner answers the away report.

## The test

Ask this of every choice; the first yes decides.

1. **Stop** if it acts outside git or beyond what the owner gave: money over the cap, game
   time outside the rules below, the owner's WH3 saves, preferences, mod list or Steam
   achievements, a ledger or account credit, deleting evidence, a re-pin, or making anything
   new public (pushing a branch counts).
2. **Stop that action** if the harness refused it (a permission prompt, the auto-mode
   classifier): do not rephrase it, route around it or write docs that pre-authorize it.
   Log one line and carry on with other work.
3. **Park** if it changes what the benchmark measures, claims or trains on: scenarios,
   suites, scores, gates, card verdicts, the failure rule, held-out sets, prompt text a model
   sees, what a policy observes, agreed checks and their tests, benchmark-defining docs,
   register rows, data and teacher use (local training too), campaign benchmark design.
   Parking is not waiting: build and test the options on a branch or in `runs/`, add one
   inbox item, take the next work. A bug found in a score, prompt or recorded result is
   parked the same way, with a count of the recorded rows the fix changes.
4. **Read only** once a [limit](#limits) is reached.
5. Otherwise **decide**: build the smallest version, write its check first, move on. A
   choice that answers a written question or sets a default goes in the away report with
   its undo command; ordinary engineering choices go in commit messages.

## Choosing work

In this order: end running work before the return
([stopping](twwarhammer3/benchmark-run.md#stopping)); work the owner named for this absence;
turning inbox items into yes/no questions backed by counts from `runs/`; objective roadmap
features, where a command or a game readback decides pass or fail against a value written
before the run (campaign infrastructure, [below](#wh3-campaign-infrastructure)); merging
exact duplicate questions and listing cleanup candidates (deleting none). Not without the
owner: battles for a question the owner did not name, paid model screens, new suite
scenarios, new doc pages, CI on the public repository.

## Checks

Before a check runs, write what it compares against, its command and its pass value, and
show once that it can fail (before the fix, or on one plausible wrong version). Report
"proposed check `<name>` passed at `<rev>` (n=...), not yet agreed", never "verified"; only
the owner adds an [agreed row](../AGENTS.md#verification-hard-rule), without a rerun. Build
on a feature only after its check passed at the same revision, and never feed a score from
an unagreed check. A chain stops at its first failed check.

## Code and main

- Play-scope code (`src/`, `configs/`, `pyproject.toml`, `uv.lock`, `.python-version`) stays
  on local, unpushed branches in worktrees outside `/tmp`: a merge changes the revision and
  the harness fingerprint `report` groups battles by. At most 3 branches wait; one line of
  work (the campaign) is one branch. On return, ask one batched merge question.
- `main` gets only other docs, tests and scripts outside the park list: whole diffs that are
  yours, the AGENTS.md test and ruff commands passing, no job running or planned.
- During an absence no agent edits this page, its AGENTS.md section, the agreed-check rows,
  the stop logic of `scripts/wh3_queue.py`, or the tests and scripts behind agreed checks.
  `owner-direction.md` takes the owner's words verbatim.
- Before a launch, commit an [Active work](state.md#active-work) line naming the agent, the
  purpose and the end time; the other agent commits nothing to `main` until it clears.

## Game time

Only while **away**, and only for: plans the owner named for this absence (a plan stopped
earlier, or arms named earlier but unplayed, need a new yes); re-runs of the agreed checks;
and `twwarhammer3 launch` + `menu` infrastructure probes whose check is written in the
probe's `runs/` folder first. Probes never use `play` or a queue and never write a register
row, score, prompt or dataset input. Every launch sets `--timeout` (a plan, `start_before`)
to end at least 60 minutes before the return, writes to an absolute path in the main
checkout's `runs/`, and, from a branch, records the branch commit and the pack's sha256.

## WH3 campaign infrastructure

The agent may build and test, in order: a save guard (a sha256 manifest of the profile's
`save_games` and `preferences.script.txt` before a campaign launch, compared after: earlier
files byte-identical, only files absent from the manifest removed); tests that every mod
script stays inert in a campaign unless the session asks; then, in the game, an unattended
campaign start, a heartbeat, a state readback, one action each (end turn, move, recruit)
with its readback, save-reload-compare, autoresolve, and handing a campaign battle to the
battle controller. Before anything loads a campaign map (the built-in campaign benchmark
too), the owner answers yes or no on harness saves and on Steam achievements, which cannot
be undone. Harness campaigns use a faction the owner has no saves for, check that cloud
saves are off, never use "continue" (it loads the newest save, maybe the owner's), change no
campaign setting and skip no AI turn; readbacks never reach a policy. Which campaign, what a
controller sees, the turn-time rule and scoring are the owner's; measured options (load and
end-turn times) go to the inbox; confirmed facts go in [integration.md](twwarhammer3/integration.md).

## Limits

Defaults per absence, for the owner to change: $0 unless the owner names a cap (counting
the ledger or the OpenRouter account use, whichever is larger); 10 reported choices; 3
waiting branches; 10 inbox items. No local training, large copy or heavy CPU/GPU job while
WH3 runs or the owner may be using the PC. Stop game work when the owner writes or the
return margin arrives; when the game closes without the harness (treat it as the owner's
return); when spend moves at a $0 cap; when the save manifest shows a changed owner file;
after two failed launches in a row; after a WSL restart (nothing resumes by itself). A new
game build is reported, never a stop, and never re-pinned alone (owner, 2026-10-18).

## On return

- **One away report**, at most 20 lines in the game's log: commits and branches, proposed
  checks with revision and n, game hours against the window, spend per ledger and account
  before and after, reported choices with undo commands, refusals. Counts are recounted
  from the register or traces and appear nowhere else.
- **One inbox**, [Owner decisions waiting](state.md#owner-decisions-waiting), at most 10
  items of at most 3 lines: the question, options with evidence and n, what stays as it is
  until answered, the one-line approval. Other pages' owner lists are linked, not copied.
  Never drop or rewrite an owner item. Silence approves nothing.
