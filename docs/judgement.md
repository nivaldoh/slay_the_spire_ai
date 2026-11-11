# Judgement calls

The owner's rule (2026-10-23): agents execute; the owner decides. A judgement call is a
choice no owner direction made that fixes what a benchmark measures, how something is
verified, what comes next, a design whose alternatives change results or their meaning, or
a parameter with benchmark or plan meaning. Agents made many such calls while the owner was
away, and they read as settled in code and docs. This page registers the goal of finding and
marking them for the owner's review; the rule for agents is in
[AGENTS.md](../AGENTS.md#judgement-calls).

## The marker

- `JUDGEMENT:` marks a call the owner has not decided. `JUDGEMENT?:` marks a spot the agent
  cannot classify; the owner categorizes it. The "?" means unsure it counts, not unsure of
  the answer.
- Text: one to three lines within 100 characters: what was chosen, who and when, the
  alternative that would change results, what rests on it. No recommendation.
- Placement: one marker per call, at the nearest convenient spot to the line that fixes it:
  a comment above it in Python, JavaScript or Lua; a plain line in a Markdown page; for a
  file that cannot carry one, a line in the page that documents it, naming the file and key.
  Never at uses, mentions or log history.
- Files that carry no marker: JSON configs (no comments); prompt files (model input, compared
  exactly by the prompt tests); the policy modules `scripted.py`, `calibration.py`, `llm.py`,
  `commander.py`, `team.py` and `skills.py` (`controllers.card()` hashes the policy's source
  file into `source_sha256`, which the card board pools on); the Lua mod (the pack hash is
  part of every card cell's setup identity); `spire/protocol.py` and `spire/policies.py`
  (byte-stable).
- List: `git grep -n JUDGEMENT -- ':!AGENTS.md' ':!docs/judgement.md'`; add `-F "JUDGEMENT?"`
  for the uncertain ones, or a branch name for unmerged drafts.

## Lifecycle

- The agent that makes or finds a call adds the marker in the same change and names the
  markers it added in its report, or says it added none.
- A marked spot may be wrong. Anything built on it says "rests on JUDGEMENT <file> <name>";
  its value is copied nowhere without the marker; a change that only holds if the call is
  right is parked, as [autonomy.md](autonomy.md) parks changes to benchmark meaning. A
  marker is not permission to decide.
- Only the owner removes or weakens a marker. An agent does so only when quoting the owner's
  words on that spot in the commit; a standing decision also gets a dated line in
  [owner-direction.md](owner-direction.md). Approval is not verification: what is verified
  is still decided by the [agreed checks](agreed-checks.md).

## Examples (format accepted 2026-10-23; the calls themselves are undecided)

- `src/twwarhammer3/battle/cards.py`, the chariot card's gate sizes: `JUDGEMENT`. An
  assistant chose 10 foil launches and 4 of the witness's first 5 on 2026-10-18 (b33/b34);
  decision 3 in [tactic-cards.md](twwarhammer3/tactic-cards.md) proposes other sizes; code
  and tests present the rule as settled.
- `src/gameai/llm.py`, `READ_TIMEOUT_S`: `JUDGEMENT?`. The raise from 60 s to 600 s was
  the assistant's response to the owner's 16k output cap. It sets each read wait;
  `post` has no total deadline, and retries affect controller waiting and billing.

## Status and how to continue

- 2026-10-23: a read-only sweep over 15 areas listed at least 225 candidates in 74 files
  (each finder was capped at 15, so this is a lower bound):
  `runs/judgement-sweep-20261023/candidates.md`, with coverage notes and three convention
  drafts beside it (`runs/` is not backed up; the sweep can be redone). Of four shortlisted
  candidates checked by three skeptics each, three carried a material error in the sweep's
  stated consequence; one, the loop's whole-batch rejection of an invalid order, had never
  fired in 640 recorded episodes.
- Next: mark in batches by area, checking each marker's text at the site first; live values
  and deciding sentences first, history never; docs any time, code and configs only between
  game jobs, in behaviour-neutral commits (a comment-only Python change keeps its syntax
  tree) whose messages give marker counts per file so the owner can sample. Date each choice
  with `git log -S` and check whether a later commit narrowed it (most errors the 2026-10-28
  reviews found were wrong dates or authors); one skeptical reviewer per batch.
- 2026-10-28: 44 markers from 12 areas; reviews found 5 wrong and 13 weak markers, all
  addressed ([log](twwarhammer3/log.md#2026-10-28-afternoon-44-judgement-markers-stats-keeps-timing-arms-apart)).
  Per-area counts, a reason for every unmarked candidate and the reviews:
  `runs/judgement-batch-20261028/` (`markers-added.txt` lists the 44 by file and line).
- 2026-10-29: `[cards]` 0-14 added 5 markers in `cards.py` (Foils; `JUDGEMENT?` Pre-registration
  label, Sampling unit, Cell identity, Foil forfeits) and a "rests on" reference to `play.py`'s
  Operator errors, Forfeit split and Wall cap. Skipped: witness cadence (the owner chose v2 at
  2 s/2 s and kept c1), contact wins (the owner's "Tell models"), `tactic-cards.md` (history).
  Three reviews: the first rejected or rewrote 6 of 7 drafts; the next two found the b35
  boundary still the assistant's (no owner-direction entry; interview question 18 asks).
  `[spire-combat]` (105-119) waits until the frozen first-combat track reopens. Tables and
  reviews: `runs/judgement-batch-20261029/`.
- On 2026-10-23 the owner had decided none of the marked calls and had not said whether the
  two examples set the right threshold. By 2026-11-05 at least 10 calls were decided (eight in
  `1fd6811`, two in `7e89ab9`); most markers stay open.
