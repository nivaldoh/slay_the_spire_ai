"""Claude Code PreToolUse hook for Bash (docs/workflow.md, stage 4): refuse `ruff format`, any
git command that moves this tree's HEAD while a WH3 queue runs, and a `git commit` in this tree
before scripts/check.py passed on exactly its files (runs/checks/last-pass.json).

AGENTS.md: most files are hand-formatted, so `ruff format` stays manual (`--check` and `--diff`
change nothing and pass); a running scripts/wh3_queue.py stops before its next job when this
tree's HEAD moves (a commit in another worktree does not). The command is split into logical
lines at newlines outside quotes; comments and heredoc bodies are text, not commands, and a
quoted mention passes. A line whose quotes never close is read as plain text. Exit 2 blocks
the call and shows the reason. A guardrail, not an enforcement boundary: aliases, variables
and scripts (`bash -c` strings among them) are not followed, and games, spending and ledgers
stay guarded in the CLI.
"""
import importlib.util
import json
import os
import re
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# git subcommands that can move HEAD (checkout and reset of paths do not; see moves_this_head).
MOVES_HEAD = {"commit", "merge", "rebase", "reset", "checkout", "switch", "pull", "cherry-pick",
              "revert", "am"}
SEPARATORS = {";", "&&", "||", "|", "&", "(", ")"}
# Words that run the next word as a command (`timeout` also takes a duration).
WRAPPERS = {"time", "nice", "env", "command", "exec", "then", "do", "else", "elif", "if", "while",
            "until", "!", "{", "}", "sudo", "xargs", "timeout"}
HEREDOC = re.compile(r"<<-?\s*\\?(['\"]?)([A-Za-z0-9_.-]+)\1")
RUFF_TEXT = re.compile(r"\bruff\s+format\b(?![^\n;&|]*--(?:check|diff)\b)")
GIT_TEXT = re.compile(r"\bgit\b[^\n;&|]*\b(" + "|".join(sorted(MOVES_HEAD)) + r")\b")
UNKNOWN = Path("/nonexistent-unknown-tree")
# Programs under which a `ruff` word runs ruff; under any other (grep, echo, git) it is text.
# `ruff`, or a pinned one as uvx takes it: ruff@0.6.9, ruff==0.6.9, "ruff >= 0.6", ruff[all].
RUFF_WORD = re.compile(r"ruff\s*($|[@=<>!~\[])", re.IGNORECASE)
RUFF_HOSTS = {"ruff", "uv", "uvx", "pipx", "xargs", "find", "parallel", "env", "nice", "time",
              "timeout", "command", "exec", "sudo"}


def logical_lines(text: str) -> list[str]:
    """Command lines split at newlines outside quotes; comments and heredoc bodies dropped."""
    out, buf, quote, waiting, i = [], [], None, [], 0
    while i < len(text):
        c = text[i]
        if quote:
            if c == "\\" and quote == '"' and i + 1 < len(text):
                buf.append(text[i:i + 2])
                i += 2
                continue
            quote = None if c == quote else quote
            buf.append(c)
        elif c == "\\" and i + 1 < len(text):
            buf.append(" " if text[i + 1] == "\n" else text[i:i + 2])
            i += 2
            continue
        elif c in "'\"":
            quote = c
            buf.append(c)
        elif c == "#" and (not buf or buf[-1][-1:] in " \t;&|("):
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
            continue
        elif (c == "<" and text[i:i + 3] != "<<<" and (i == 0 or text[i - 1] != "<")
              and not text[i - 1:i].isdigit() and not in_arithmetic(text, i)
              and (found := HEREDOC.match(text, i))):
            waiting.append(found.group(2))
            buf.append(found.group(0))
            i = found.end()
            continue
        elif c == "\n":
            out.append("".join(buf))
            buf = []
            i += 1
            while waiting:  # skip each heredoc's body, through its delimiter line
                end = text.find("\n", i)
                line, i = (text[i:], len(text)) if end < 0 else (text[i:end], end + 1)
                if line.strip() == waiting[0]:
                    waiting.pop(0)
                elif i >= len(text):
                    waiting = []
            continue
        else:
            buf.append(c)
        i += 1
    out.append("".join(buf))
    return [line for line in out if line.strip()]


def in_arithmetic(text: str, i: int) -> bool:
    """Position i is inside `((...))` on its line, where `<<` is a shift."""
    before = text[text.rfind("\n", 0, i) + 1:i]
    return before.count("((") > before.count("))")


def commands(line: str) -> list[list[str]]:
    """The simple commands in one line, as word lists, with ["("] and [")"] marking subshells;
    ValueError if its quotes do not close."""
    lexer = shlex.shlex(line, posix=True, punctuation_chars=";&|()")
    lexer.whitespace_split = True
    lexer.commenters = ""  # logical_lines already dropped comments; `a#b` is one word
    out, current = [], []
    for word in lexer:
        if word in SEPARATORS:
            out.append(current)
            out.append([word] if word in ("(", ")") else [])
            current = []
        else:
            current.append(word)
    return [c for c in out + [current] if c]


def program(words: list[str]) -> list[str]:
    """The words from the program on: assignments and wrappers skipped."""
    while words and (words[0] in WRAPPERS or re.match(r"[A-Za-z_][A-Za-z0-9_]*=", words[0])
                     or (words[0].startswith("-") and len(words) > 1)):
        takes_value = words[0] in ("timeout", "-n", "-u", "-s", "-k", "-g", "--unset")
        words = words[2:] if takes_value and len(words) > 2 else words[1:]
    return words


def place(cwd: Path, path: str) -> Path:
    """Where `cd path` or `-C path` leads; UNKNOWN for a path through a variable."""
    return UNKNOWN if "$" in path else (cwd / os.path.expanduser(path)).resolve()


def is_this_tree(where: Path) -> bool:
    """The nearest .git above `where` is this repository's own directory."""
    for folder in (where, *where.parents):
        if (folder / ".git").exists():
            return folder == ROOT and (folder / ".git").is_dir()
    return False


def moves_this_head(words: list[str], cwd: Path) -> str | None:
    """`git [-C dir] [-c k=v] [--flag] SUB ...` in this tree -> SUB if it moves HEAD."""
    if not words or Path(words[0]).name != "git":
        return None
    rest, where = words[1:], cwd
    while rest and rest[0].startswith("-"):
        if rest[0] == "-C" and len(rest) > 1:
            where = place(where, rest[1])
        rest = rest[2:] if rest[0] in ("-C", "-c") else rest[1:]
    if not rest or rest[0] not in MOVES_HEAD or not is_this_tree(where):
        return None
    sub, args = rest[0], rest[1:]
    if sub in ("checkout", "reset") and "--" in args:
        return None  # restores files
    paths = [a for a in args if not a.startswith("-") and a != "HEAD"]
    if sub == "reset" and all((where / a).exists() for a in paths) and not (
            {"--soft", "--hard", "--mixed", "--keep", "--merge"} & set(args) and paths):
        return None  # unstages paths, or resets the index to HEAD
    return sub


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


CHECK_REASON = ("`git commit` before scripts/check.py passed on this exact tree: run it in its own "
                "command, read its result, then commit (AGENTS.md: before each commit)")


def tree_checked(root: Path = ROOT) -> bool:
    """scripts/check.py's last pass covered exactly the files now in this tree."""
    try:
        record = json.loads((root / "runs/checks/last-pass.json").read_text())
        spec = importlib.util.spec_from_file_location("check_script", root / "scripts/check.py")
        check = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(check)
        return record.get("tree") == check.tree_content(root)
    except (OSError, ValueError, AttributeError):
        return False


def refusal(text: str, *, queue: bool, cwd: Path = ROOT, checked=lambda: True) -> str | None:
    for line in logical_lines(text):
        try:
            parsed = commands(line)
        except ValueError:  # quotes that never close: judge the plain text
            if RUFF_TEXT.search(line):
                return RUFF_REASON
            if queue and (found := GIT_TEXT.search(line)) and is_this_tree(cwd):
                return git_reason(found.group(1))
            continue
        outer = []
        for words in parsed:
            if words == ["("]:
                outer.append(cwd)  # a subshell's cd ends with it
                continue
            if words == [")"]:
                cwd = outer.pop() if outer else cwd
                continue
            host = Path(words[0]).name
            words = program(words)
            if words and words[0] in ("cd", "pushd") and len(words) > 1:
                cwd = place(cwd, words[1])
                continue
            for i, word in enumerate(words):
                # ruff run by a host program (uv, python -m, xargs, find ...), not a grep
                # pattern or echoed text; its options may come before `format`.
                hosts = {host, Path(words[0]).name}
                runs_ruff = bool(RUFF_WORD.match(Path(word).name)) and bool(
                    hosts & RUFF_HOSTS or any(h.startswith("python") for h in hosts))
                if runs_ruff and "format" in words[i + 1:] and not (
                        {"--check", "--diff"} & set(words[i + 1:])):
                    return RUFF_REASON
            sub = moves_this_head(words, cwd)
            if queue and sub:
                return git_reason(sub)
            if sub == "commit" and not checked():
                return CHECK_REASON
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
        text = event["tool_input"]["command"]
    except (ValueError, KeyError, TypeError):
        return 0
    reason = refusal(text, queue=queue_running(), cwd=Path(event.get("cwd") or ROOT).resolve(),
                     checked=tree_checked)
    if reason:
        print(reason, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
