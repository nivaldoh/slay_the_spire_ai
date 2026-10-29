"""The exit gate: Ruff, the whole offline test suite and risky-edit warnings in one command.

    uv run --locked python scripts/check.py [--base REV]

Run it before every commit and quote its first five lines in the report: the revision, whether
the tree is clean, the counts, the skip reasons and the log path (the whole output is kept under
runs/checks/). It exits 1 when Ruff or any test fails or pytest cannot run, otherwise 0. The
suite runs without WH3_WRITE_PROMPTS, so it never rewrites prompt snapshots, and its scratch
directory (runs/test-scratch/check-<pid>) is removed after a pass.

Warnings follow and never change the exit code. "needs your yes" names an edit only the owner
approves, found in the changes since --base (default: the merge base with origin/main, so
unpushed commits, uncommitted and untracked files all count): lines removed or changed in a file
an agreed check names (docs/agreed-checks.md) or in that page; an edited or removed JUDGEMENT
line; an assert removed or changed under tests/; a skip or xfail added there; a changed prompt
snapshot; a package added or a version changed in uv.lock. A line moved verbatim elsewhere
(indentation and comment marks aside) is neither removed nor added. Last, "markers" counts the
marker problems listed in the log (docs/judgement.md); only the owner changes markers, so they
never fail.

Nothing here launches a game, spends money or commits. Followed: CPython's
Tools/patchcheck/patchcheck.py (one command reports what a change touched, measured from its
base branch) and transformers' `make check-repository-consistency` (repository rules as plain
checks; ours are tests/test_repo_rules.py, which the suite runs).
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import textwrap
import tomllib
from collections import Counter
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGREED = "docs/agreed-checks.md"
SNAPSHOTS = "tests/twwarhammer3/prompts/*.txt"
# docs/judgement.md, "Files that carry no marker".
NO_MARKER = ("*.json", "configs/*prompt*.md", "tests/twwarhammer3/prompts/*",
             "src/twwarhammer3/mod/*", "src/spire/protocol.py", "src/spire/policies.py",
             *(f"src/twwarhammer3/battle/{name}.py"
               for name in ("scripted", "calibration", "llm", "commander", "team", "skills")))
RULE_PAGES = ("AGENTS.md", "docs/judgement.md")  # state the rule; the listing skips them too
ASSERT = re.compile(r"^\s*(assert\b|with pytest\.raises\b|pytest\.raises\()")
SKIP = re.compile(r"pytest\.(skip|xfail|importorskip)\(|pytest\.mark\.(skip|skipif|xfail)\b")
MARKER = re.compile(r"(?<!`)JUDGEMENT\??:")
DATED = re.compile(r"\b(20\d\d-\d\d-\d\d|\d\d-\d\d|[vb]\d[\w.]*)\b|author unrecorded")
RESTS_ON = re.compile(r"rests? on JUDGEMENT\??\s+`?([\w./-]+\.\w+)`?")
MISSPELT = re.compile(r"\bJUDG[M]ENT")
SUMMARY = re.compile(r"\d+ (passed|failed|skipped|errors?|xfailed|xpassed)\b.* in [\d.]+s")
SKIPPED = re.compile(r"^SKIPPED \[(\d+)\] \S+?:\d+: (.*)$", re.M)


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                          check=True).stdout


def changes(root: Path, base: str) -> tuple[dict[str, tuple[list, list]], set[str]]:
    """Removed and added lines per path from base to the working tree, and the deleted paths.
    Untracked files that Git does not ignore count as added."""
    found: dict[str, tuple[list, list]] = {}
    header, path = False, ""
    for line in git(root, "diff", "--no-renames", "--no-color", "-U0", base, "--").splitlines():
        if line.startswith("diff --git "):
            rest = line[len("diff --git "):]  # "a/P b/P": renames are off, so both are P
            path, header = rest[2:2 + (len(rest) - 5) // 2], True
            found[path] = ([], [])
        elif line.startswith("@@"):
            header = False
        elif not header and line[:1] in "-+":
            found[path][line[0] == "+"].append(line[1:])
    for name in git(root, "ls-files", "-z", "--others", "--exclude-standard").split("\0"):
        if name:
            try:
                found[name] = ([], (root / name).read_text(encoding="utf-8").splitlines())
            except (OSError, UnicodeDecodeError):
                found[name] = ([], [])
    deleted = git(root, "diff", "--no-renames", "--name-only", "--diff-filter=D", base, "--")
    return found, set(deleted.split())


def net(removed: list[tuple[str, str]], added: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """(path, line) pairs removed and not added back verbatim anywhere in the same set."""
    def key(line: str) -> str:
        return re.sub(r"^[\s#/*-]+", "", line).strip()
    left = Counter(key(line) for _, line in added)
    kept = []
    for path, line in removed:
        if left[key(line)]:
            left[key(line)] -= 1
        elif key(line):
            kept.append((path, line))
    return kept


def agreed_paths(root: Path) -> set[str]:
    """Files and directories under tests/, scripts/ or src/ that an agreed check names."""
    text = (root / AGREED).read_text(encoding="utf-8") if (root / AGREED).exists() else ""
    return {p.rstrip(".,;:)") for p in re.findall(r"\b((?:tests|scripts|src)/[\w./-]+)", text)}


def lock_versions(text: str) -> dict[str, str]:
    versions: dict[str, set[str]] = {}
    for package in tomllib.loads(text).get("package", []):
        versions.setdefault(package["name"], set()).add(package.get("version", "?"))
    return {name: "/".join(sorted(v)) for name, v in versions.items()}


def where(pairs: list[tuple[str, str]], limit: int = 3) -> str:
    shown = "; ".join(f"{path}: {line.strip()[:60]}" for path, line in pairs[:limit])
    return shown + (f" (+{len(pairs) - limit} more)" if len(pairs) > limit else "")


def warnings(root: Path, base: str) -> list[str]:
    """The "needs your yes" lines for the changes since base."""
    found, deleted = changes(root, base)
    out = []

    def lines(side: int, keep) -> list[tuple[str, str]]:
        return [(p, line) for p, pair in found.items() for line in pair[side] if keep(p, line)]

    agreed = agreed_paths(root)
    def in_agreed(path: str, _line: str = "") -> bool:
        return path == AGREED or any(path == a or path.startswith(a + "/") for a in agreed)
    # JUDGEMENT?: Agreed-check edits — Claude, 2026-10-29: lines removed or changed, net of
    # verbatim moves, and deleted named files; pure additions (new tests) pass silently.
    gone = sorted(p for p in deleted if p in agreed)
    changed = net(lines(0, in_agreed), lines(1, in_agreed))
    if gone or changed:
        files = sorted({p for p, _ in changed} | set(gone))
        out.append(f"an agreed check's files lose or change lines: {', '.join(files)}")
    marked = net(lines(0, lambda p, line: "JUDGEMENT" in line),
                 lines(1, lambda p, line: "JUDGEMENT" in line))
    if marked:
        out.append(f"JUDGEMENT line removed or edited: {where(marked)}")

    def is_test(path: str, _line: str = "") -> bool:
        return path.startswith("tests/") and path.endswith(".py")
    asserts = net(lines(0, lambda p, line: is_test(p) and ASSERT.match(line)),
                  lines(1, lambda p, line: is_test(p) and ASSERT.match(line)))
    if asserts:
        out.append(f"{len(asserts)} assertion line(s) removed or changed: {where(asserts)}")
    skips = net(lines(1, lambda p, line: is_test(p) and SKIP.search(line)),
                lines(0, lambda p, line: is_test(p) and SKIP.search(line)))
    if skips:
        out.append(f"{len(skips)} skip or xfail added: {where(skips)}")
    snapshots = sorted(p for p, (r, a) in found.items() if fnmatch(p, SNAPSHOTS) and (r or a))
    snapshots += sorted(p for p in deleted if fnmatch(p, SNAPSHOTS) and p not in snapshots)
    if snapshots:
        out.append(f"prompt snapshots changed: {', '.join(snapshots)}")
    if "uv.lock" in found and "uv.lock" not in deleted:
        try:
            old = lock_versions(git(root, "show", f"{base}:uv.lock"))
        except subprocess.CalledProcessError:
            old = {}
        new = lock_versions((root / "uv.lock").read_text(encoding="utf-8"))
        moved = [f"{name} {old.get(name, 'new')} -> {version}"
                 for name, version in sorted(new.items()) if old.get(name) != version]
        if moved:
            out.append(f"uv.lock adds or changes packages: {', '.join(moved)}")
    return out


def marker_problems(root: Path) -> list[str]:
    """Marker lines that break docs/judgement.md's format, for the owner to sort out."""
    listed = git(root, "grep", "-l", "-I", "--untracked", "-e", "JUDGEMENT", "-e", "JUDG" "MENT")
    every = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard").split("\0")
    problems = []
    for name in listed.split():
        if name in RULE_PAGES:
            continue
        lines = (root / name).read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, 1):
            if MISSPELT.search(line):
                problems.append(f"{name}:{number}: spelled without the first E")
            mark = MARKER.search(line)
            if not mark:
                continue
            if any(fnmatch(name, pattern) for pattern in NO_MARKER):
                problems.append(f"{name}:{number}: this file cannot carry a marker")
            if not DATED.search(" ".join([line[mark.end():], *lines[number:number + 2]])):
                problems.append(f"{name}:{number}: no date or version in its first three lines")
        if name.endswith("log.md"):
            continue  # history keeps the paths of its day
        for target in RESTS_ON.findall(" ".join(lines)):
            # From the root, or the tail of a path ("team/check_wh3_team.py", "proposal.md").
            paths = [root / target, *(root / f for f in every if f.endswith("/" + target))]
            path = next((p for p in paths if p.is_file()), None)
            if path is None:
                problems.append(f"{name}: rests on JUDGEMENT {target}, which does not exist")
            elif not MARKER.search(path.read_text(encoding="utf-8", errors="replace")):
                problems.append(f"{name}: rests on JUDGEMENT {target}, which has no marker")
    return list(dict.fromkeys(problems))


def skip_reasons(output: str) -> str:
    reasons: Counter[str] = Counter()
    for count, reason in SKIPPED.findall(output):
        reasons[textwrap.shorten(reason.split(": ")[0], 60, placeholder=" ...")] += int(count)
    return "; ".join(f"{n} {reason}" for reason, n in reasons.most_common()) or "none"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", help="revision the warnings compare with "
                        "(default: the merge base with origin/main, else HEAD)")
    args = parser.parse_args()
    head = git(ROOT, "rev-parse", "--short", "HEAD").strip()
    branch = git(ROOT, "branch", "--show-current").strip() or "detached HEAD"
    status = git(ROOT, "status", "--porcelain").splitlines()
    untracked = sum(line.startswith("??") for line in status)
    try:
        base = args.base or git(ROOT, "merge-base", "HEAD", "origin/main").strip()
    except subprocess.CalledProcessError:
        base = "HEAD"

    env = {k: v for k, v in os.environ.items() if k != "WH3_WRITE_PROMPTS"}
    scratch = ROOT / "runs" / "test-scratch" / f"check-{os.getpid()}"
    scratch.parent.mkdir(parents=True, exist_ok=True)  # pytest makes only the last folder
    ruff = subprocess.run([sys.executable, "-m", "ruff", "check", "."], cwd=ROOT, env=env,
                          capture_output=True, text=True)
    tests = subprocess.run([sys.executable, "-m", "pytest", "-q", "-ra", f"--basetemp={scratch}"],
                           cwd=ROOT, env=env, capture_output=True, text=True)
    output = tests.stdout + tests.stderr
    summary = next((line.strip("= ") for line in reversed(output.splitlines())
                    if SUMMARY.search(line)), f"no pytest summary (exit {tests.returncode})")
    passed = ruff.returncode == 0 and tests.returncode == 0
    found = [line for line in ruff.stdout.splitlines() if line.startswith("Found")]
    lint = "Ruff clean" if ruff.returncode == 0 else (
        f"Ruff FAILED ({(found or [f'exit {ruff.returncode}'])[-1]})")
    first = [line for line in output.splitlines() if line.startswith(("FAILED ", "ERROR "))][:3]

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log = ROOT / "runs" / "checks" / f"{stamp}-{head}-{os.getpid()}.log"
    shown = [
        f"revision  {head} on {branch}",
        "tree      " + (f"dirty: {len(status) - untracked} changed, {untracked} untracked"
                        if status else "clean"),
        f"result    {'PASSED' if passed else 'FAILED'}: {lint}; {summary}",
        f"skipped   {skip_reasons(output)}",
        f"log       {log.relative_to(ROOT)}",
    ]
    shown += [f"          {line}" for line in first]
    yes = warnings(ROOT, base)
    if yes:
        shown.append(f"needs your yes (changes since {base[:9]}):")
        shown += [f"  - {line}" for line in yes]
    problems = marker_problems(ROOT)
    if problems:
        shown.append(f"markers   {len(problems)} problems listed in the log, for the owner")
    print("\n".join(shown))

    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("\n".join([*shown, "", "== marker problems", *problems, "",
                              "== git status --porcelain", *status, "",
                              "== ruff check .", ruff.stdout + ruff.stderr,
                              "== pytest -q -ra", output]), encoding="utf-8")
    if passed:
        shutil.rmtree(scratch, ignore_errors=True)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
