"""scripts/check.py's risky-edit warnings and marker list, on a small Git repository.

Each planted edit must print its "needs your yes" line, and an unrelated edit none (light
factory plan, stage 1). Whether check.py's suite counts match plain pytest's was compared by
hand; see the docstring of scripts/check.py for what each warning means.
"""

import importlib.util
import subprocess
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "check_script", Path(__file__).resolve().parents[1] / "scripts" / "check.py")
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)

# Split, so check.py finds no marker, reference or skip of this file's own.
MARK = "JUDGEMENT" + ":"
RESTS = "rests on " + "JUDGEMENT"
SKIP, IMPORTORSKIP = "@pytest.mark." + "skip", "pytest." + "importorskip"
LOCK = '[[package]]\nname = "{0}"\nversion = "{1}"\n'
BASE = {
    "docs/agreed-checks.md": "- Thing: `uv run --locked pytest -ra tests/agreed/test_a.py`.\n",
    "tests/agreed/test_a.py": "def test_a():\n    assert 1 == 1\n",
    "tests/other/test_b.py": "import pytest\n\n\ndef test_b():\n    assert 2 == 2\n",
    "tests/twwarhammer3/prompts/llm.txt": "You command an army.\n",
    "docs/page.md": f"Intro.\n\n{MARK} Thing — Claude, 2026-10-29: X, not Y.\n",
    "src/pkg/mod.py": "def f():\n    return 1\n",
    "uv.lock": LOCK.format("a", "1.0"),
}


def git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    for name, text in BASE.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", ".")
    git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
    return tmp_path


def edit(root, name, old, new):
    path = root / name
    path.write_text(path.read_text().replace(old, new))


PLANTED = {
    "agreed test line": (lambda r: edit(r, "tests/agreed/test_a.py", "def test_a", "def test_a2"),
                         "an agreed check's files lose or change lines: tests/agreed/test_a.py"),
    "agreed test deleted": (lambda r: (r / "tests/agreed/test_a.py").unlink(),
                            "an agreed check's files lose or change lines: tests/agreed/test_a.py"),
    "agreed page": (lambda r: edit(r, "docs/agreed-checks.md", "Thing", "Other"),
                    "an agreed check's files lose or change lines: docs/agreed-checks.md"),
    "marker": (lambda r: edit(r, "docs/page.md", "X, not Y", "X"),
               "JUDGEMENT line removed or edited: docs/page.md"),
    "assert": (lambda r: edit(r, "tests/other/test_b.py", "2 == 2", "True"),
               "1 assertion line(s) removed or changed: tests/other/test_b.py"),
    "skip": (lambda r: edit(r, "tests/other/test_b.py", "def", f"{SKIP}\ndef"),
             "1 skip or xfail added: tests/other/test_b.py"),
    "untracked skip": (lambda r: (r / "tests/other/test_c.py").write_text(
        f"import pytest\n\n{IMPORTORSKIP}('torch')\n"),
        "1 skip or xfail added: tests/other/test_c.py"),
    "snapshot": (lambda r: edit(r, "tests/twwarhammer3/prompts/llm.txt", "army", "host"),
                 "prompt snapshots changed: tests/twwarhammer3/prompts/llm.txt"),
    "lock": (lambda r: (r / "uv.lock").write_text(LOCK.format("a", "1.1") + LOCK.format("b", "2")),
             "uv.lock adds or changes packages: a 1.0 -> 1.1, b new -> 2"),
}


@pytest.mark.parametrize("case", PLANTED)
def test_each_risky_edit_needs_a_yes(repo, case):
    plant, expected = PLANTED[case]
    plant(repo)
    found = check.warnings(repo, "HEAD")
    assert len(found) == 1 + (case == "agreed test deleted") and found[0].startswith(expected)


def test_unrelated_edits_and_verbatim_moves_need_no_yes(repo):
    edit(repo, "docs/page.md", "Intro.", "A longer intro.")
    edit(repo, "src/pkg/mod.py", "return 1\n", "return 1\n\n\ndef g():\n    return 2\n")
    (repo / "tests/agreed/test_new.py").write_text("def test_new():\n    assert 3 == 3\n")
    # A marker and an assert moved verbatim, into a comment and another test file.
    edit(repo, "docs/page.md", f"{MARK} Thing — Claude, 2026-10-29: X, not Y.\n", "")
    edit(repo, "src/pkg/mod.py", "def f", f"# {MARK} Thing — Claude, 2026-10-29: X, not Y.\ndef f")
    edit(repo, "tests/other/test_b.py", "    assert 2 == 2\n", "    pass\n")
    (repo / "tests/other/test_d.py").write_text("def test_d():\n    assert 2 == 2\n")
    assert check.warnings(repo, "HEAD") == []


def test_marker_problems_are_listed(repo):
    (repo / "docs/bad.md").write_text(
        f"{MARK} no who or when here.\n\n"
        f"Mentioning `{MARK}` in code is fine. A JUDG" "MENT typo.\n"
        f"This {RESTS} `src/pkg/mod.py` Thing, and {RESTS} `docs/gone.md` X.\n"
        f"And {RESTS} `page.md` Thing, beside this page.\n")
    (repo / "configs.json").write_text(f'{{"note": "{MARK} Thing, 2026-10-29"}}\n')
    assert check.marker_problems(repo) == [
        "configs.json:1: this file cannot carry a marker",
        "docs/bad.md:1: no date or version in its first three lines",
        "docs/bad.md:3: spelled without the first E",
        f"docs/bad.md: {RESTS} src/pkg/mod.py, which has no marker",
        f"docs/bad.md: {RESTS} docs/gone.md, which does not exist",
    ]
