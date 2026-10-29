"""Remove one refusal at a time from a source file, score each version with a test command, and
list the removals no test catches (a one-operator mutation test, the idea behind mutmut and
PIT; not checked against their code). The `refusal-sweep` skill says when and how to run it.

    python scripts/refusal_sweep.py SCRATCH FILE PATTERN REPLACEMENT [TESTS ...]

SCRATCH is a checkout to plant in, normally `git worktree add --detach runs/<task>/scratch`;
FILE is relative to it. For Lua, PATTERN is a regex for the refusal's start (e.g.
`(?<![\\w.:])error\\(`), replaced one at a time by REPLACEMENT (e.g. `tostring(`). For Python they
are ignored: each raised `X(...)` (from the syntax tree) becomes a bare `X(...)`, its `from`
clause dropped, and a version that does not parse is reported, never scored. "caught" = the
tests exit nonzero (with -x); a run past SWEEP_TIMEOUT seconds (default 120) is HANG, counted
caught; the unplanted baseline must pass first, and SCRATCH may not be this tree. Every run is
without bytecode (planted copies share a size, and a cached .pyc of the previous plant once ran
in a plant's place, 2026-10-29). SWEEP_PYTHON overrides the interpreter. Offline only: plant
near a launch only after stubbing its first step.
"""
import ast
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

S, FILE, PATTERN, REPLACEMENT, *TESTS = sys.argv[1:]
S = Path(S).resolve()
if S == Path(__file__).resolve().parents[1]:
    sys.exit("plant in a scratch checkout (git worktree add --detach), never this tree")
TIMEOUT = float(os.environ.get("SWEEP_TIMEOUT", "120"))
PY = os.environ.get("SWEEP_PYTHON", sys.executable)
# A bare environment: no Windows PATH entries (so no Windows program can start), no bytecode,
# no model downloads.
ENV = {"PYTHONPATH": "src", "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1",
       "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HOME": os.environ["HOME"]}
# The saved-evidence replays plant their own values and do not import the swept files.
DESELECT = ["-k", "not test_the_saved_case_passes_and_each_planted_wrong_value_fails_it"
            " and not test_each_planted_wrong_value_fails_the_check"]


def run():
    # No bytecode: planted copies share a size, and a WSL clock step can give two of them the
    # same mtime second, so a cached .pyc of the previous plant would run (found 2026-10-29).
    for cache in list(S.rglob("__pycache__")):
        shutil.rmtree(cache, ignore_errors=True)
    try:
        r = subprocess.run([PY, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-x",
                            *DESELECT, *TESTS], cwd=S, env=ENV, capture_output=True, text=True,
                           timeout=TIMEOUT)
    except subprocess.TimeoutExpired:  # a removed timeout can leave a test waiting forever
        return "hang", "", f"no result within {TIMEOUT:g} s"
    first = re.findall(r"^FAILED (.+?)(?: - |$)", r.stdout, re.M)
    return r.returncode, (first or [""])[0], (r.stdout.strip().splitlines() or ["?"])[-1]


path = S / FILE
original = path.read_text()
code, _, last = run()
print(f"baseline: exit {code}: {last}", flush=True)
if code != 0:
    sys.exit("the unplanted baseline fails; fix it before sweeping")


def variants():
    """(line, start, end, replacement) per site. Python goes through the syntax tree: the whole
    `raise X(...) [from e]` statement becomes `X(...)`, so the file still parses (a plain text
    edit of `raise X(...) from e` is a SyntaxError, which a run would count as caught)."""
    if FILE.endswith(".py"):
        lines = original.splitlines(keepends=True)
        starts = [0]
        for line in lines:
            starts.append(starts[-1] + len(line))

        def offset(lineno, byte_col):  # ast columns count UTF-8 bytes, not characters
            return starts[lineno - 1] + len(lines[lineno - 1].encode()[:byte_col].decode())
        for node in ast.walk(ast.parse(original)):
            if (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)
                    and isinstance(node.exc.func, ast.Name) and node.exc.func.id[:1].isupper()):
                yield (node.lineno, offset(node.lineno, node.col_offset),
                       offset(node.end_lineno, node.end_col_offset),
                       ast.get_source_segment(original, node.exc))
    else:
        for m in re.finditer(PATTERN, original):
            yield original.count("\n", 0, m.start()) + 1, m.start(), m.end(), REPLACEMENT


sites = sorted(variants())
missed, sites_invalid = 0, []
for line, start, end, replacement in sites:
    text = original[original.rfind("\n", 0, start) + 1:original.index("\n", start)]
    mutated = original[:start] + replacement + original[end:]
    if FILE.endswith(".py"):
        try:
            ast.parse(mutated)  # never score a version that does not parse
        except SyntaxError:
            print(f"INVALID (does not parse, not counted): {FILE}:{line} {text.strip()[:80]}",
                  flush=True)
            sites_invalid.append(line)
            continue
    path.write_text(mutated)
    try:
        code, first, last = run()
    finally:
        path.write_text(original)
    missed += not code
    verdict = "HANG" if code == "hang" else "caught" if code else "MISSED"
    print(f"{verdict}: {FILE}:{line} {text.strip()[:80]}" + (f"  <- {first}" if first else ""),
          flush=True)
counted = len(sites) - len(sites_invalid)
print(f"{counted - missed} of {counted} removals caught or hung")
