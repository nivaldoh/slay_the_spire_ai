"""The exit gate: Ruff, the whole offline test suite and risky-edit warnings in one command.

    uv run --locked python scripts/check.py [--base REV]

Run it before every commit and quote its first five lines in the report: the revision, whether
the tree is clean, the counts, the skip reasons and the log path (the whole output is kept under
runs/checks/). It exits 1 when Ruff or any test fails or pytest cannot run, otherwise 0. The
suite runs without WH3_WRITE_PROMPTS, so it never rewrites prompt snapshots, and its scratch
directory (runs/test-scratch/check-<pid>) is removed after a pass.

A passing run whose files did not change while it ran writes runs/checks/last-pass.json with a hash
of every file not ignored (tree_content); scripts/githooks/pre-commit refuses a commit unless the
hash still matches, and a failing run deletes it.

Each run also appends one line to runs/checks/agreed-passes.jsonl (owner, 2026-10-29: "(a)"):
for every entry of docs/agreed-checks.md with a pytest command, whether that command's tests
passed in this run, read from pytest's JUnit XML. A line counts for its revision only when
`at_revision` is true. The line comes from the whole suite, not the command run alone.

Warnings follow and never change the exit code. "needs your yes" names an edit only the owner
approves, found in the changes since --base (default: the merge base with origin/main, so
unpushed commits, uncommitted and untracked files all count): lines removed or changed in a file
an agreed check names (docs/agreed-checks.md) or in that page; an edited or removed JUDGEMENT
line; an assert removed or changed under tests/; a skip or xfail added there; a changed prompt
snapshot; a package added or a version changed in uv.lock. A line moved verbatim elsewhere
(indentation and comment marks aside) is neither removed nor added. "pages" names docs/state.md
when it is over its 120 lines (AGENTS.md; a warning at the owner's yes, 2026-10-30).
"worktree" says the run is in a linked worktree, where tests of saved evidence can skip.
Last, "markers" counts the marker problems listed in the log (docs/judgement.md); only the
owner changes markers, so they never fail.

`--plants` instead replays tests/plants.toml, the planted wrong versions the named tests must
catch, in a scratch worktree at HEAD, one at a time and without bytecode: each line says caught,
MISSED, HANG (counted caught, as in scripts/refusal_sweep.py) or stale (its text is gone), after
each test set has passed unplanted. It exits 1 on a miss, a stale plant or a failing baseline.
Followed: the night's plant scripts (runs/agreed-planted-20261029/plant.py: "caught" means a
listed test fails) and mutmut's idea of rerunning known mutants; not checked against its code.

Nothing here launches a game, spends money or commits. Followed: CPython's
Tools/patchcheck/patchcheck.py (one command reports what a change touched, measured from its
base branch) and transformers' `make check-repository-consistency` (repository rules as plain
checks; ours are tests/test_repo_rules.py, which the suite runs).
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import textwrap
import tomllib
import xml.etree.ElementTree as ElementTree
from collections import Counter
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGREED = "docs/agreed-checks.md"
PASSES = "runs/checks/agreed-passes.jsonl"
CHECKED = "runs/checks/last-pass.json"  # the tree the last passing run checked
PLANTS = "tests/plants.toml"
STATE, STATE_LINES = "docs/state.md", 120
PLANT_TIMEOUT_S = 300
# The stale-plant rule fails whenever a plant is applied (its text is gone), so a replay leaves
# it out; otherwise every plant listing tests/test_check_script.py would count as caught.
STALE_RULE = ("tests/test_check_script.py::"
              "test_each_committed_plant_still_applies_and_names_real_tests")
PYTEST_CALL = re.compile(r"`[^`]*\bpytest\b([^`]*)`")
OTHER_CALL = re.compile(r"`(?![^`]*\bpytest\b)[^`]*\b(?:python|twwarhammer3 \w+|spire \w+)\b[^`]*`")
SNAPSHOTS = "tests/twwarhammer3/prompts/*.txt"
# docs/judgement.md, "Files that carry no marker".
NO_MARKER = ("*.json", "configs/*prompt*.md", "tests/twwarhammer3/prompts/*",
             "src/twwarhammer3/mod/*", "src/spire/protocol.py", "src/spire/policies.py",
             *(f"src/twwarhammer3/battle/{name}.py"
               for name in ("scripted", "calibration", "llm", "commander", "team", "skills")))
RULE_PAGES = ("AGENTS.md", "docs/judgement.md")  # state the rule; the listing skips them too
# The owner's untracked thesis notes (the link test skips them too); their markers and links
# are the owner's, and listing them in every run was only noise (owner, 2026-10-29).
PRIVATE = "docs/thesis/"
ASSERT = re.compile(r"^\s*(assert\b|with pytest\.raises\b|pytest\.raises\()")
SKIP = re.compile(r"pytest\.(skip|xfail|importorskip)\(|pytest\.mark\.(skip|skipif|xfail)\b")
MARKER = re.compile(r"(?<!`)JUDGEMENT\??:")
DATED = re.compile(r"\b(20\d\d-\d\d-\d\d|\d\d-\d\d|[vb]\d[\w.]*)\b|author unrecorded")
RESTS_ON = re.compile(r"rests? on JUDGEMENT\??\s+`?([\w./-]+\.\w+)`?")
MISSPELT = re.compile(r"\bJUDG[M]ENT")
SUMMARY = re.compile(r"\d+ (passed|failed|skipped|errors?|xfailed|xpassed)\b.* in [\d.]+s")
SKIPPED = re.compile(r"^SKIPPED \[(\d+)\] \S+?:\d+: (.*)$", re.M)


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, encoding="utf-8",
                          errors="replace", check=True).stdout


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
                found[name] = ([], (root / name).read_text(encoding="utf-8",
                                                           errors="replace").splitlines())
            except OSError:
                found[name] = ([], [])
    deleted = git(root, "diff", "--no-renames", "--name-only", "--diff-filter=D", base, "--")
    return found, set(deleted.split())


def net(removed: list[tuple[str, str]], added: list[tuple[str, str]],
        marks: bool = False) -> list[tuple[str, str]]:
    """(path, line) pairs removed and not added back verbatim anywhere in the same set.
    Indentation counts (in Python it is meaning); with marks, leading comment marks and
    spaces do not, so a marker can move between a page and a comment."""
    def key(line: str) -> str:
        return re.sub(r"^[\s#/*-]+", "", line).strip() if marks else line.rstrip()
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


def agreed_pytest(root: Path) -> dict[str, list[str]]:
    """Each agreed check's pytest targets, by its entry's text before the first colon. An entry
    that also runs a live or other command (a check_wh3_*.py, `rl confirm`) is named
    "<entry> (pytest part only)": its line says nothing about that command. Targets only:
    options such as -k are not applied."""
    text = (root / AGREED).read_text(encoding="utf-8") if (root / AGREED).exists() else ""
    checks = {}
    for entry in re.split(r"\n(?=- )", text):
        targets = [arg for call in PYTEST_CALL.findall(entry) for arg in call.split()
                   if not arg.startswith("-")]
        if entry.startswith("- ") and targets:
            name = " ".join(entry[2:].split(":")[0].split())
            checks[name + (" (pytest part only)" if OTHER_CALL.search(entry) else "")] = targets
    return checks


def junit_cases(junit: Path) -> list[tuple[str, str]]:
    """(dotted test address, passed/failed/skipped) per test case in pytest's JUnit XML; an
    unreadable report is one nameless failure."""
    cases = []
    try:
        for case in ElementTree.parse(junit).getroot().iter("testcase"):
            outcome = ("failed" if case.find("failure") is not None or case.find("error")
                       is not None else "skipped" if case.find("skipped") is not None
                       else "passed")
            # pytest's junitxml names a test tests.dir.test_file[.Class].test_name[params]; a
            # collection error has no class and its module as the name.
            name, classname = (case.get("name") or "").split("[")[0], case.get("classname")
            cases.append((f"{classname}.{name}" if classname else name,
                          outcome if name else "failed"))
    except (OSError, ElementTree.ParseError):
        cases = [("", "failed")]
    return cases


def selected(cases: list[tuple[str, str]], target: str) -> list[tuple[str, str]]:
    """The cases a pytest target (directory, file or node) selects."""
    parts = target.split("[")[0].split("::")
    dotted = ".".join([parts[0].rstrip("/").removesuffix(".py").replace("/", "."), *parts[1:]])
    return [(address, outcome) for address, outcome in cases
            if address == dotted or address.startswith(dotted + ".")]


def outcomes(cases: list[tuple[str, str]], target: str) -> list[str]:
    return [outcome for _, outcome in selected(cases, target)]


def agreed_results(root: Path, junit: Path) -> dict[str, dict]:
    """Per agreed check, its tests in this run. It passed when every target ran a test (a
    missing node makes its own command exit 4), none failed or errored, and at least one
    passed: stricter than pytest, whose exit is 0 when all are skipped. An unreadable or
    interrupted report (a test case without a name) passes none."""
    cases = junit_cases(junit)
    interrupted = any(not address.strip(".") for address, _ in cases)
    results = {}
    for name, targets in agreed_pytest(root).items():
        found, every = Counter(), True
        for target in targets:
            mine = outcomes(cases, target)
            found.update(mine)
            every = every and bool(mine)
        results[name] = {"passed": every and found["passed"] > 0 and found["failed"] == 0
                         and not interrupted,
                         "tests": sum(found.values()), "skipped": found["skipped"],
                         "failed": found["failed"]}
    return results


def at_revision(root: Path) -> tuple[bool, list[str], list[str]]:
    """Whether the tested files are HEAD's, with the changed and the counted untracked paths.

    JUDGEMENT?: Pass at a revision — Claude, 2026-10-29, under the owner's "(a)": untracked
    Markdown and anything under docs/ may sit beside it (the thesis notes and the owner's TODO
    always do); any other untracked or changed file makes the pass not HEAD's. Counting every
    untracked file would credit no revision; ignoring them all would credit untracked tests.
    """
    changed = sorted({line[3:] for line in git(root, "status", "--porcelain",
                                               "--untracked-files=no").splitlines()})
    untracked = git(root, "ls-files", "--others", "--exclude-standard").splitlines()
    loose = [p for p in untracked if not (p.startswith("docs/") or p.endswith(".md"))]
    return not changed and not loose, changed, loose


def still_at_revision(root: Path, revision: str,
                      before: tuple[bool, list[str], list[str]]) -> tuple[bool, list, list]:
    """at_revision for a whole run: the files were HEAD's before it (``before``, at
    ``revision``) and still are after it, with HEAD unmoved; changed and untracked paths of both
    reads. An edit made and undone during the run is not seen."""
    after = at_revision(root)
    own = before[0] and after[0] and git(root, "rev-parse", "HEAD").strip() == revision
    return own, sorted({*before[1], *after[1]}), sorted({*before[2], *after[2]})


def plant_list(root: Path) -> list[dict]:
    path = root / PLANTS
    return tomllib.loads(path.read_text(encoding="utf-8")).get("plant", []) if path.exists() else []


def stale_plants(root: Path) -> list[str]:
    """Plants whose `old` text no longer occurs exactly once in their file."""
    stale = []
    for plant in plant_list(root):
        path = root / plant["file"]
        count = path.read_text(encoding="utf-8").count(plant["old"]) if path.is_file() else 0
        if count != 1:
            stale.append(f"{plant['id']}: its text occurs {count} times in {plant['file']}")
    return stale


def plant_changes(root: Path, base: str) -> list[str]:
    """Plants at `base` that are gone or differ now, by id; a new plant needs no yes."""
    try:
        before = tomllib.loads(git(root, "show", f"{base}:{PLANTS}")).get("plant", [])
    except (subprocess.CalledProcessError, tomllib.TOMLDecodeError):
        return []
    try:
        now = {plant.get("id"): plant for plant in plant_list(root)}
    except tomllib.TOMLDecodeError:
        return [f"{PLANTS} does not parse"]
    found = []
    for plant in before:
        current = now.get(plant.get("id"))
        if current is None:
            found.append(f"{plant.get('id')} removed")
        elif current != plant:
            fields = sorted(k for k in {*plant, *current} if plant.get(k) != current.get(k))
            found.append(f"{plant.get('id')} changed ({', '.join(fields)})")
    return found


def plant_tests(scratch: Path, targets: list[str], junit: Path) -> tuple[list | None, str]:
    """(cases, output) of `targets` run in `scratch` (its src/ first, no bytecode): cases is
    None on a timeout and [] when pytest wrote no report. A bare PATH keeps Windows programs out
    (as scripts/refusal_sweep.py). An interrupt kills the tests before it goes on."""
    env = {"PYTHONPATH": "src", "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1",
           "HOME": os.environ.get("HOME", ""), "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
    junit.unlink(missing_ok=True)  # a run that writes none must not read the last plant's
    tmp = scratch / "runs" / "test-scratch" / "plant"  # test scratch in runs/, as AGENTS.md says
    tmp.parent.mkdir(parents=True, exist_ok=True)  # pytest makes only the last folder
    process = subprocess.Popen([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                                f"--basetemp={tmp}", f"--junitxml={junit}",
                                f"--deselect={STALE_RULE}", *targets],
                               cwd=scratch, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        output, _ = process.communicate(timeout=PLANT_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        return None, ""
    except BaseException:  # Ctrl-C, or SIGTERM through plants_main: no tests left running
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        raise
    return (junit_cases(junit) if junit.exists() else []), output


def tail(output: str, lines: int = 1) -> str:
    return " / ".join(output.strip().splitlines()[-lines:]) or "no output"


def copy_evidence(scratch: Path) -> None:
    """Copy the saved evidence plants name (`evidence = [paths under runs/]`) from the main
    checkout into the scratch worktree: copies, so a planted wrong version can never write into
    the only real copy, and removed with the worktree. A missing source is left missing, so that
    plant's tests skip and its baseline fails."""
    main = Path(git(ROOT, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()).parent
    named = (item for plant in plant_list(scratch) for item in plant.get("evidence", []))
    for item in dict.fromkeys(named):
        source, copy = main / item, scratch / item
        if source.exists() and not copy.exists():
            copy.parent.mkdir(parents=True, exist_ok=True)
            (shutil.copytree if source.is_dir() else shutil.copy2)(source, copy)


def replay_plants(scratch: Path) -> list[tuple[str, str, str]]:
    """(verdict, line, pytest output) per plant in the checkout `scratch`. Each test set first
    runs unplanted and must pass, every target with at least one test passing."""
    plants, junit = plant_list(scratch), scratch.with_name(scratch.name + ".xml")
    baselines = {}
    for targets in dict.fromkeys(tuple(plant["tests"]) for plant in plants):
        cases, output = plant_tests(scratch, list(targets), junit)
        good = cases is not None and all("passed" in (mine := outcomes(cases, target))
                                         and "failed" not in mine for target in targets)
        baselines[targets] = (good, output)
    stale = {line.split(":")[0] for line in stale_plants(scratch)}
    report = []
    for plant in plants:
        name, targets = plant["id"], tuple(plant["tests"])
        if name in stale:
            report.append(("stale", f"{name}: its text is no longer in {plant['file']}", ""))
            continue
        good, output = baselines[targets]
        if not good:
            report.append(("baseline", f"{name}: unplanted, its tests fail, skip or are missing:"
                                       f" {tail(output)}", output))
            continue
        path = scratch / plant["file"]
        original = path.read_text(encoding="utf-8")
        path.write_text(original.replace(plant["old"], plant["new"]), encoding="utf-8")
        try:
            cases, output = plant_tests(scratch, list(targets), junit)
        finally:
            path.write_text(original, encoding="utf-8")
        failing = [address for target in targets
                   for address, outcome in selected(cases or [], target) if outcome == "failed"]
        if cases is None:
            report.append(("HANG", f"{name}: no result in {PLANT_TIMEOUT_S} s (counted caught)",
                           ""))
        elif not cases:
            report.append(("NOREPORT", f"{name}: pytest wrote no report: {tail(output)}", output))
        elif failing:
            more = f" and {len(failing) - 1} more" if len(failing) > 1 else ""
            report.append(("caught", f"{name}: {failing[0]}{more}", ""))
        else:
            report.append(("MISSED", f"{name} ({plant['guards']}): no failure in"
                                     f" {', '.join(targets)}: {tail(output)}", output))
    junit.unlink(missing_ok=True)
    return report


def plants_main() -> int:
    # SIGTERM (an agent's command timeout) runs the finally blocks: plant restored, tests
    # killed, scratch worktree removed.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    head = git(ROOT, "rev-parse", "--short", "HEAD").strip()
    scratch = ROOT / "runs" / "test-scratch" / f"plants-{os.getpid()}"
    scratch.parent.mkdir(parents=True, exist_ok=True)
    git(ROOT, "worktree", "add", "--detach", str(scratch), "HEAD")
    try:
        probe = subprocess.run([sys.executable, "-c", "import gameai; print(gameai.__file__)"],
                               cwd=scratch, env={"PYTHONPATH": "src", "PATH": "/usr/bin:/bin"},
                               capture_output=True, text=True).stdout.strip()
        if not probe.startswith(str(scratch)):
            print(f"plants   not run: the scratch checkout imports {probe or 'nothing'}")
            return 1
        copy_evidence(scratch)
        report = replay_plants(scratch)
    finally:
        git(ROOT, "worktree", "remove", "--force", str(scratch))
    counts = Counter(verdict for verdict, _, _ in report)
    dirty = len(git(ROOT, "status", "--porcelain", "--untracked-files=no").splitlines())
    log = ROOT / "runs" / "checks" / (f"plants-{datetime.now():%Y%m%d-%H%M%S}-{head}"
                                      f"-{os.getpid()}.log")
    shown = [f"plants   {len(report)} at {head}" + (f" ({dirty} uncommitted changes not in it)"
                                                    if dirty else "") + ": "
             + ", ".join(f"{n} {verdict}" for verdict, n in counts.most_common()),
             f"log      {log.relative_to(ROOT)}",
             *(f"  {verdict}: {line}" for verdict, line, _ in report if verdict != "caught")]
    print("\n".join(shown))
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("\n".join([*shown, "", *(f"{v}: {line}" for v, line, _ in report), "",
                              *(f"== {line.split(':')[0]}\n{output}" for _, line, output in report
                                if output)]) + "\n", encoding="utf-8")
    return 0 if set(counts) <= {"caught", "HANG"} else 1


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
    plants = plant_changes(root, base)
    if plants:
        out.append(f"planted versions removed or changed ({PLANTS}; updating one to new code"
                   f" counts too): {'; '.join(plants)}")
    marked = net(lines(0, lambda p, line: "JUDGEMENT" in line),
                 lines(1, lambda p, line: "JUDGEMENT" in line), marks=True)
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
        if name in RULE_PAGES or name.startswith(PRIVATE):
            continue
        lines = (root / name).read_text(encoding="utf-8", errors="replace").splitlines()
        history = Path(name).name == "log.md"
        for number, line in enumerate(lines, 1):
            if MISSPELT.search(line):
                problems.append(f"{name}:{number}: spelled without the first E")
            mark = MARKER.search(line)
            if not mark:
                continue
            if any(fnmatch(name, pattern) for pattern in NO_MARKER):
                problems.append(f"{name}:{number}: this file cannot carry a marker")
            if history:
                problems.append(f"{name}:{number}: a marker in log history")
            if not DATED.search(" ".join([line[mark.end():], *lines[number:number + 2]])):
                problems.append(f"{name}:{number}: no date or version in its first three lines")
        if history:
            continue  # history keeps the paths of its day
        for target in RESTS_ON.findall(" ".join(lines)):
            # From the root, or the tail of a path ("team/check_wh3_team.py", "proposal.md");
            # a bare name may match several files, and any one with a marker will do.
            paths = [root / target, *(root / f for f in every if f.endswith("/" + target))]
            paths = [p for p in paths if p.is_file()]
            if not paths:
                problems.append(f"{name}: rests on JUDGEMENT {target}, which does not exist")
            elif not any(MARKER.search(p.read_text(encoding="utf-8", errors="replace"))
                         for p in paths):
                problems.append(f"{name}: rests on JUDGEMENT {target}, which has no marker")
    return list(dict.fromkeys(problems))


def tree_content(root: Path) -> str:
    """sha256 of the path and content of every file on disk that git does not ignore, tracked or
    not. The index and HEAD are left out, so staging (a deletion or rename included) or committing
    part of a checked tree keeps it; any edit, new file or deletion changes it.
    Symlinks contribute their target text, including directory and dangling links.

    JUDGEMENT?: Checked tree — Claude, 2026-10-30, for the commit guard draft: only the owner's
    untracked thesis notes (PRIVATE, docs/thesis/) are left out; everything else counts, prompts
    and another session's edits included. Counting the notes would block commits whenever the owner
    edits one; leaving out more (all Markdown) would let an unchecked prompt be committed."""
    digest = hashlib.sha256()
    names = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard").split("\0")
    for name in sorted({n for n in names if n}):
        path = root / name
        if name.startswith(PRIVATE):
            continue
        if path.is_symlink():
            digest.update(name.encode() + b"\0symlink\0"
                          + hashlib.sha256(os.fsencode(os.readlink(path))).digest())
        elif path.is_file():
            digest.update(name.encode() + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def long_pages(root: Path) -> list[str]:
    """docs/state.md when it is over its line budget; a warning only."""
    page = root / STATE
    lines = len(page.read_text(encoding="utf-8").splitlines()) if page.exists() else 0
    return [f"{STATE} has {lines} lines, over {STATE_LINES}"] if lines > STATE_LINES else []


def linked_worktree(root: Path) -> list[str]:
    """In a linked worktree, a note: the tests that read the main checkout's runs/ evidence can
    skip here, so a pass here may cover less than one there."""
    main = Path(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()).parent
    if main == root.resolve():
        return []
    return [f"a linked worktree of {main}: tests that read its runs/ evidence can skip here; "
            "run check.py there, after merging, before counting a pass"]


def skip_reasons(output: str) -> str:
    reasons: Counter[str] = Counter()
    for count, reason in SKIPPED.findall(output):
        reasons[textwrap.shorten(reason.split(": ")[0], 60, placeholder=" ...")] += int(count)
    return "; ".join(f"{n} {reason}" for reason, n in reasons.most_common()) or "none"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", help="revision the warnings compare with "
                        "(default: the merge base with origin/main, else HEAD)")
    parser.add_argument("--plants", action="store_true",
                        help=f"replay {PLANTS} at HEAD instead (a few minutes)")
    try:
        args = parser.parse_args()
    except SystemExit as exc:
        if exc.code:  # rejected arguments fail the check; --help is not a run
            (ROOT / CHECKED).unlink(missing_ok=True)
        raise
    if args.plants:
        return plants_main()
    # JUDGEMENT?: Concurrent passes — Codex, 2026-10-30, owner "Use your best judgement":
    # a genuine pass on current contents can survive another run's abort. Invalidating it
    # would force an extra run; this guard's concurrent behavior rests on this.
    (ROOT / CHECKED).unlink(missing_ok=True)
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
    content = tree_content(ROOT)
    ruff = subprocess.run([sys.executable, "-m", "ruff", "check", "."], cwd=ROOT, env=env,
                          capture_output=True, text=True)
    junit = scratch.with_name(scratch.name + ".xml")  # beside --basetemp, which pytest clears
    revision, before = git(ROOT, "rev-parse", "HEAD").strip(), at_revision(ROOT)
    tests = subprocess.run([sys.executable, "-m", "pytest", "-q", "-ra", f"--basetemp={scratch}",
                            f"--junitxml={junit}"], cwd=ROOT, env=env, capture_output=True,
                           text=True)
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
    agreed = agreed_results(ROOT, junit)
    junit.unlink(missing_ok=True)
    own, changed, untracked = still_at_revision(ROOT, revision, before)
    shown.append(f"agreed    {sum(r['passed'] for r in agreed.values())} of {len(agreed)} "
                 "agreed-check pytest commands passed"
                 f"{'' if own else ' (not at HEAD: tree changed)'}; {PASSES}")
    yes = warnings(ROOT, base)
    if yes:
        shown.append(f"needs your yes (changes since {base[:9]}):")
        shown += [f"  - {line}" for line in yes]
    shown += [f"pages     {line} (AGENTS.md Working habits)" for line in long_pages(ROOT)]
    shown += [f"worktree  {line}" for line in linked_worktree(ROOT)]
    unchanged = tree_content(ROOT) == content
    if passed and not unchanged:
        shown.append("record    none: files changed while it ran, so a commit stays refused; "
                     "run it again")
    problems = marker_problems(ROOT)
    if problems:
        shown.append(f"markers   {len(problems)} problems listed in the log, for the owner")
    print("\n".join(shown))

    log.parent.mkdir(parents=True, exist_ok=True)
    with (ROOT / PASSES).open("a", encoding="utf-8") as passes:
        passes.write(json.dumps({
            "time": datetime.now().isoformat(timespec="seconds"),
            "revision": revision, "at_revision": own,
            "changed": changed, "untracked": untracked, "log": str(log.relative_to(ROOT)),
            "checks": agreed}) + "\n")
    log.write_text("\n".join([*shown, "", "== marker problems", *problems, "",
                              "== git status --porcelain", *status, "",
                              "== ruff check .", ruff.stdout + ruff.stderr,
                              "== pytest -q -ra", output]), encoding="utf-8")
    record = ROOT / CHECKED
    if passed and unchanged:  # scripts/githooks/pre-commit lets a commit of this tree through
        record.write_text(json.dumps({"tree": content, "revision": revision,
                                      "log": str(log.relative_to(ROOT))}) + "\n")
    else:
        record.unlink(missing_ok=True)
    if passed:
        shutil.rmtree(scratch, ignore_errors=True)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
