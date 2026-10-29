"""Claude Code PreToolUse hook for Bash (docs/workflow.md, stage 4): refuse `ruff format`, and
any git command that moves this tree's HEAD while a WH3 queue runs.

AGENTS.md: most files are hand-formatted, so `ruff format` stays manual (`--check` and `--diff`
change nothing and pass); a running scripts/wh3_queue.py stops before its next job when this
tree's HEAD moves (a commit in another worktree does not). The command is read line by line
as shell words; heredoc bodies are text, not commands, and a quoted mention passes. A line
whose quotes do not close is read as plain text. Exit 2 blocks the call and shows the reason.
A guardrail, not an enforcement boundary: aliases and scripts are not followed, and games,
spending and ledgers stay guarded in the CLI.
"""
import json
import re
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# git subcommands that move HEAD.
MOVES_HEAD = {"commit", "merge", "rebase", "reset", "checkout", "switch", "pull", "cherry-pick",
              "revert", "am"}
SEPARATORS = {";", "&&", "||", "|", "&", "(", ")"}
# Words that run the next word as a command (`timeout` also takes a duration).
WRAPPERS = {"time", "nice", "env", "command", "exec", "then", "do", "else", "elif", "if", "while",
            "until", "!", "{", "}", "sudo", "xargs", "timeout"}
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
RUFF_TEXT = re.compile(r"\bruff\s+format\b(?![^\n;&|]*--(?:check|diff)\b)")
GIT_TEXT = re.compile(r"\bgit\b[^\n;&|]*\b(" + "|".join(sorted(MOVES_HEAD)) + r")\b")


def lines(text: str) -> list[str]:
    """The command lines of a shell text: continuations joined, heredoc bodies dropped."""
    out, delimiter = [], None
    for line in text.replace("\\\n", " ").split("\n"):
        if delimiter is not None:
            if line.strip() == delimiter:
                delimiter = None
            continue
        out.append(line)
        found = HEREDOC.search(line)
        delimiter = found.group(2) if found else None
    return out


def commands(line: str) -> list[list[str]]:
    """The simple commands in one line, as word lists; ValueError if its quotes do not close."""
    lexer = shlex.shlex(line, posix=True, punctuation_chars=";&|()")
    lexer.whitespace_split = True
    out, current = [], []
    for word in lexer:
        if word in SEPARATORS:
            out.append(current)
            current = []
        else:
            current.append(word)
    return [c for c in out + [current] if c]


def program(words: list[str]) -> list[str]:
    """The words from the program on: assignments and wrappers skipped."""
    while words and (words[0] in WRAPPERS or re.match(r"[A-Za-z_][A-Za-z0-9_]*=", words[0])
                     or (words[0].startswith("-") and len(words) > 1)):
        words = words[2:] if words[0] == "timeout" and len(words) > 2 else words[1:]
    return words


def moves_this_head(words: list[str], cwd: Path) -> str | None:
    """`git [-C dir] [-c k=v] [--flag] SUB ...` run in this tree -> SUB if it moves HEAD."""
    if not words or Path(words[0]).name != "git":
        return None
    rest, where = words[1:], cwd
    while rest and rest[0].startswith("-"):
        if rest[0] == "-C" and len(rest) > 1:
            where = (where / rest[1]).resolve()
        rest = rest[2:] if rest[0] in ("-C", "-c") else rest[1:]
    if not rest or rest[0] not in MOVES_HEAD or not where.is_relative_to(ROOT):
        return None
    return None if Path(where / ".git").is_file() else rest[0]  # a linked worktree's .git is a file


def queue_running(proc: Path = Path("/proc")) -> bool:
    """A Python process running scripts/wh3_queue.py (not a shell or tool that names it)."""
    for cmdline in proc.glob("[0-9]*/cmdline"):
        try:
            argv = cmdline.read_bytes().decode(errors="replace").split("\0")
        except OSError:
            continue
        if argv and Path(argv[0]).name.startswith("python") and any(
                Path(arg).name == "wh3_queue.py" for arg in argv[1:]):
            return True
    return False


RUFF_REASON = ("`ruff format` rewrites hand-formatted files (AGENTS.md); use `ruff format --diff` "
               "to look, or edit by hand")


def git_reason(sub: str) -> str:
    return (f"`git {sub}` while scripts/wh3_queue.py runs: a moved HEAD stops the queue before "
            "its next job, so commit nothing in this tree until it ends (AGENTS.md)")


def refusal(text: str, *, queue: bool, cwd: Path = ROOT) -> str | None:
    for line in lines(text):
        try:
            parsed = commands(line)
        except ValueError:  # unclosed quotes: judge the plain text
            if RUFF_TEXT.search(line):
                return RUFF_REASON
            if queue and (found := GIT_TEXT.search(line)):
                return git_reason(found.group(1))
            continue
        for words in parsed:
            words = program(words)
            if words and words[0] == "cd" and len(words) > 1:
                cwd = (cwd / words[1]).resolve()
                continue
            for i, word in enumerate(words[:-1]):
                if Path(word).name == "ruff" and words[i + 1] == "format" and not (
                        {"--check", "--diff"} & set(words[i + 2:])):
                    return RUFF_REASON
            sub = moves_this_head(words, cwd)
            if queue and sub:
                return git_reason(sub)
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
        text = event["tool_input"]["command"]
    except (ValueError, KeyError, TypeError):
        return 0
    reason = refusal(text, queue=queue_running(), cwd=Path(event.get("cwd") or ROOT))
    if reason:
        print(reason, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
