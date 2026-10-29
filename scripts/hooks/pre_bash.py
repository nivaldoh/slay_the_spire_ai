"""Claude Code PreToolUse hook for Bash (docs/workflow.md, stage 4): refuse `ruff format`, and
any git command that moves HEAD while a WH3 queue runs.

AGENTS.md: most files are hand-formatted, so `ruff format` stays manual (`--check` and `--diff`
change nothing and pass); a running scripts/wh3_queue.py stops before its next job when HEAD
moves. The command is split into shell words, so a quoted mention ("ruff format" in a grep)
passes. Exit 2 blocks the call and shows the reason; anything unparsable passes. A guardrail,
not an enforcement boundary: games, spending and ledgers stay guarded in the CLI.
"""
import json
import shlex
import sys
from pathlib import Path

# git subcommands that move HEAD (a commit, merge or checkout restarts nothing else).
MOVES_HEAD = {"commit", "merge", "rebase", "reset", "checkout", "switch", "pull", "cherry-pick",
              "revert", "am"}
SEPARATORS = {";", "&&", "||", "|", "&", "(", ")", "\n"}


def commands(text: str) -> list[list[str]]:
    """The simple commands in a shell line, as word lists."""
    lexer = shlex.shlex(text, posix=True, punctuation_chars=";&|()\n")
    lexer.whitespace_split = True
    out, current = [], []
    for word in lexer:
        if word in SEPARATORS:
            out.append(current)
            current = []
        else:
            current.append(word)
    return [c for c in out + [current] if c]


def git_subcommand(words: list[str]) -> str | None:
    """`git [-C dir] [-c k=v] [--flag] SUB ...` -> SUB."""
    if Path(words[0]).name != "git":
        return None
    rest = words[1:]
    while rest and rest[0].startswith("-"):
        rest = rest[2:] if rest[0] in ("-C", "-c") else rest[1:]
    return rest[0] if rest else None


def queue_running(proc: Path = Path("/proc")) -> bool:
    for cmdline in proc.glob("[0-9]*/cmdline"):
        try:
            if b"wh3_queue.py" in cmdline.read_bytes():
                return True
        except OSError:
            continue
    return False


def refusal(text: str, *, queue: bool) -> str | None:
    try:
        parsed = commands(text)
    except ValueError:
        return None
    for words in parsed:
        for i, word in enumerate(words[:-1]):
            if Path(word).name == "ruff" and words[i + 1] == "format" and not (
                    {"--check", "--diff"} & set(words[i + 2:])):
                return ("`ruff format` rewrites hand-formatted files (AGENTS.md); use "
                        "`ruff format --diff` to look, or edit by hand")
        sub = git_subcommand(words)
        if queue and sub in MOVES_HEAD:
            return (f"`git {sub}` while scripts/wh3_queue.py runs: a moved HEAD stops the "
                    "queue before its next job, so commit nothing until it ends (AGENTS.md)")
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
        text = event["tool_input"]["command"]
    except (ValueError, KeyError, TypeError):
        return 0
    reason = refusal(text, queue=queue_running())
    if reason:
        print(reason, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
