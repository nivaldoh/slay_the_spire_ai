# Context loading for Codex and Claude Code

The shared startup instructions route each goal to its required sections. Detailed game
commands and implementation conventions live in [development.md](development.md); current
work stays in [state.md](state.md). This page is the audit record, not extra startup reading.
Owner request: [2026-11-09](owner-direction.md). Baseline: `2a560d3`.

## What loads and when

| Layer | Codex | Claude Code |
|---|---|---|
| Repository instructions | Global guidance, then the root-to-working-directory `AGENTS.md` chain at startup; nearer instructions take precedence | This repo's `CLAUDE.md` imports `AGENTS.md`; keep that single import |
| More specific instructions | Do not assume opening an arbitrary source file reloads the startup chain; explicitly follow the root's game routes | Ancestor instruction files load at launch; descendant files load when files in their subtree are used |
| Ordinary linked docs | Read explicitly when the task route requires them | Ordinary links defer reading; `@` imports load with their parent |
| Skills | Names/descriptions/paths initially; chosen bodies later | Descriptions initially; chosen bodies later |
| Personal memory | None found in the inspected `~/.codex/memories/` | `MEMORY.md` startup index; topic files on demand |
| Hooks | Project `PreToolUse` and `Stop` only | Same events/scripts; no project `SessionStart` injection |

Sources: OpenAI [instruction discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
and [skills](https://learn.chatgpt.com/docs/build-skills); Anthropic
[memory and imports](https://code.claude.com/docs/en/memory) and
[skills](https://code.claude.com/docs/en/skills), read 2026-11-09.
The explicit Codex read rule is a conservative inference from startup discovery.
Local CLI versions: Codex 0.167.0 and Claude Code 2.1.319; the app's injected context may differ.

Claude's current docs also support native `AGENTS.md` discovery, conditional on settings and
version. The import remains supported and avoids dependence on those settings. Instructions,
memory, catalogs, tool definitions and conversation history all consume context; shortening
repository files cannot remove platform instructions or already-loaded text in this session.

## Audit and changes

Measured UTF-8 bytes, not tokens, from the files on 2026-11-09:

| Startup source | Before | After |
|---|---:|---:|
| Shared `AGENTS.md` | 13,211 bytes / 200 lines | 8,556 bytes / 118 lines |
| Claude `CLAUDE.md` import | 11 bytes / 1 line | unchanged |
| Claude personal memory index | 9,666 bytes | 1,232 bytes |
| Claude global search-pattern rule | 338 bytes / 6 lines | 96 bytes / 1 line |

The shared instruction reduction is 4,655 bytes (35.2%). The moved development sections
remain mandatory for their matching tasks. `state.md` was 16,743 bytes and `workflow.md`
42,593 bytes; neither is imported automatically. The new reading routes select sections,
so their complete sizes are not claimed as automatic startup savings. Bytes saved do not
establish token cost, latency or better task execution.

The audit found six repetitions of one search-pattern rule in `~/.claude/CLAUDE.md`, and a
memory index containing dated outcomes and completed or pending plans. The applied personal
change collapses the repeated rule and moves the old memory index, including every link, to
an on-demand topic index. Repository directions and current evidence decide what is true now.
The separate filesystem-approved write preserved all 76 topic links and backed up the
originals in `runs/context-loading-20261109/personal-backup/`. The reproducible change,
checksums and backups stay local, outside Git.

JUDGEMENT?: Context routing — Codex, 2026-11-09, under the owner's optimization goal: keep
hard constraints at root and route implementation details by task. Loading every section
up front is the alternative; retrieval and byte comparisons rest on this choice.

The [reading table](workflow.md#start-here) now covers status questions, research, approved
actions, source changes and live-job conflicts. Search headings or a distinctive topic;
read the smallest section that supplies the required rule and its dependencies. A new goal
should not reload a whole guidance file already present in context. A resumed goal checks
current Git/process evidence before repeating an action recorded in its handoff.

No plugin or hook settings changed. This session exposes many plugin skill descriptions
beyond the two repository skills; the local Claude settings enable frontend-design and
universal-modder. Catalog availability is distinct from loading a skill body. Review actual
usage before disabling useful capabilities. For a later targeted experiment, Claude's
`skillOverrides` can make a selected non-plugin skill `user-invocable-only`; plugin skills
are excluded from that setting and are managed through `/plugin`. A smaller Codex
`skills.max_context_tokens` budget can omit skills, so it is not a free saving.
These are documented controls, not settings applied here. [Claude skills](https://code.claude.com/docs/en/skills),
[Codex skills](https://learn.chatgpt.com/docs/build-skills).

## Evidence and follow-up

Card, raw checks, preservation map, independent review and handoff:
`runs/context-loading-20261109/`. Existing link and agent-sync checks cover file relationships,
not whether a model obeys the routes. No agreed method establishes session efficiency yet.

The existing [Context comparison proposal](workflow.md#session-context-improvements) stays
unagreed. For a future comparison, hold each tool's version, model, configuration, working
directory and prompt fixed; use fresh sessions for both revisions. Use sibling or isolated
checkouts for that comparison: a worktree nested inside main can inherit main's ancestor
instructions in Claude as well as its own. Separate automatic
startup context from subsequent tool reads, cached input from uncached input, and latency
from owner intervention. Claude's `/context all` lists memory files; inspect the actual
Codex instruction chain/transcript rather than assuming byte counts are token counts.
Keep required-rule retrieval and task correctness alongside cost. Anthropic recommends
short instructions with concrete checks; see [best practices](https://code.claude.com/docs/en/best-practices).

The static route audit covers the proposal's five cases: a status question reaches its
current evidence; an approved action reaches its authority; a running-game conflict reaches
the root constraints and command scope; WH3-only code reaches development and WH3 guidance;
shared code affecting Spire also reaches `docs/spire/AGENTS.md`. It cannot establish actual
model adherence, session speed, full personal-memory parity or native hook behavior.
