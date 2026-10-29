"""scripts/check.py's risky-edit warnings and marker list, on a small Git repository.

Each planted edit must print its "needs your yes" line, and an unrelated edit none (light
factory plan, stage 1). Whether check.py's suite counts match plain pytest's was compared by
hand; see the docstring of scripts/check.py for what each warning means.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "check_script", Path(__file__).resolve().parents[1] / "scripts" / "check.py")
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)

# Split, so check.py finds no marker, reference or skip of this file's own.
MARK = "JUDGEMENT" + ":"
RESTS = "rests on " + "JUDGEMENT"
SKIP, XFAIL = "@pytest.mark." + "skipif(True, reason='x')", "@pytest.mark." + "xfail"
IMPORTORSKIP = "pytest." + "importorskip"
LOCK = '[[package]]\nname = "{0}"\nversion = "{1}"\n'
BASE = {
    "docs/agreed-checks.md": "- Thing: `uv run --locked pytest -ra tests/agreed/test_a.py`.\n",
    "tests/agreed/test_a.py": "def test_a():\n    assert 1 == 1\n",
    "tests/other/test_b.py": "import pytest\n\n\ndef test_b():\n    assert 2 == 2\n"
                             "    with pytest.raises(ValueError):\n        int('x')\n",
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
    "assert indented away": (lambda r: edit(r, "tests/other/test_b.py", "    assert 2",
                                             "    if False:\n        assert 2"),
                              "1 assertion line(s) removed or changed: tests/other/test_b.py"),
    "raises": (lambda r: edit(r, "tests/other/test_b.py", "    with pytest.raises(ValueError):\n"
                              "        int('x')\n", ""),
               "1 assertion line(s) removed or changed: tests/other/test_b.py"),
    "skip": (lambda r: edit(r, "tests/other/test_b.py", "def", f"{SKIP}\ndef"),
             "1 skip or xfail added: tests/other/test_b.py"),
    "xfail": (lambda r: edit(r, "tests/other/test_b.py", "def", f"{XFAIL}\ndef"),
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
        f"And {RESTS} `page.md` Thing, beside this page.\n"
        f"A bare name matching two files, the second marked: {RESTS} `tool.py` Thing.\n")
    for folder, text in (("aa", "x = 1\n"), ("zz", f"# {MARK} Thing — Claude, 2026-10-29: X.\n")):
        (repo / "src" / folder).mkdir()
        (repo / "src" / folder / "tool.py").write_text(text)
    (repo / "configs.json").write_text(f'{{"note": "{MARK} Thing, 2026-10-29"}}\n')
    assert check.marker_problems(repo) == [
        "configs.json:1: this file cannot carry a marker",
        "docs/bad.md:1: no date or version in its first three lines",
        "docs/bad.md:3: spelled without the first E",
        f"docs/bad.md: {RESTS} src/pkg/mod.py, which has no marker",
        f"docs/bad.md: {RESTS} docs/gone.md, which does not exist",
    ]


def test_each_agreed_pytest_command_is_read_from_this_runs_junit(repo):
    (repo / "docs/agreed-checks.md").write_text(
        "- File: `uv run --locked pytest -ra tests/agreed/test_a.py`; agreed 2026-10-29.\n"
        "- Nodes: `uv run pytest tests/agreed/test_a.py::TestK::test_k\n"
        "  tests/other/test_b.py::test_b`; agreed: twice.\n"
        "- Fails: `pytest -ra tests/other/test_fail.py`.\n"
        "- Renamed: `pytest tests/agreed/test_a.py::test_gone`.\n"
        "- Half renamed: `pytest tests/agreed/test_a.py::test_a tests/agreed/test_a.py::test_g`.\n"
        "- Live too: `pytest -ra tests/agreed/test_a.py::test_a`; live: `uv run --locked python\n"
        "  tests/agreed/check_live.py --output x`.\n"
        "- Skipped: `pytest tests/other/test_skip.py`.\n"
        "- Live only: `uv run --locked python tests/agreed/check_live.py --output x`.\n")
    edit(repo, "tests/agreed/test_a.py", "def test_a", "import pytest\n\n\n"
         "class TestK:\n    @pytest.mark.parametrize('n', [1, 2])\n"
         "    def test_k(self, n):\n        assert n\n\n\ndef test_a")
    (repo / "pytest.ini").write_text("[pytest]\n")  # its own rootdir, wherever tmp_path is
    (repo / "tests/agreed/test_ab.py").write_text("def test_ab():\n    assert 1 == 1\n")
    (repo / "tests/other/test_fail.py").write_text("def test_f():\n    assert 1 == 2\n\n\n"
                                                   "def test_e(no_such_fixture):\n    pass\n")
    (repo / "tests/other/test_skip.py").write_text(f"import pytest\n\n\n{SKIP}\ndef test_s():\n"
                                                   "    assert 1 == 1\n")
    junit = repo / "junit.xml"
    subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                    f"--junitxml={junit}", "tests"], cwd=repo, capture_output=True)
    result = check.agreed_results(repo, junit)
    assert result == {
        "File": {"passed": True, "tests": 3, "skipped": 0, "failed": 0},
        "Nodes": {"passed": True, "tests": 3, "skipped": 0, "failed": 0},
        "Fails": {"passed": False, "tests": 2, "skipped": 0, "failed": 2},
        "Renamed": {"passed": False, "tests": 0, "skipped": 0, "failed": 0},
        "Half renamed": {"passed": False, "tests": 1, "skipped": 0, "failed": 0},
        "Live too (pytest part only)": {"passed": True, "tests": 1, "skipped": 0, "failed": 0},
        "Skipped": {"passed": False, "tests": 1, "skipped": 1, "failed": 0},
    }


@pytest.mark.parametrize("plant,own", [
    (lambda r: None, True),
    (lambda r: [(r / p).write_text("x\n") for p in ("docs/new.md", "docs/a.png", "tests/N.md")],
     True),
    (lambda r: (r / "tests/other/test_new.py").write_text("def test_n():\n    pass\n"), False),
    (lambda r: edit(r, "src/pkg/mod.py", "1", "2"), False),
    (lambda r: (edit(r, "src/pkg/mod.py", "1", "2"), git(r, "add", "src/pkg/mod.py")), False),
])
def test_a_pass_counts_for_head_only_with_its_files(repo, plant, own):
    plant(repo)
    assert check.at_revision(repo)[0] is own


def test_an_interrupted_or_unreadable_run_passes_no_agreed_check(repo):
    # A KeyboardInterrupt that escapes a test ends the session; pytest's report then holds a
    # test case without a name.
    (repo / "tests/other/test_stop.py").write_text(
        "def test_stop():\n    raise KeyboardInterrupt\n")
    (repo / "pytest.ini").write_text("[pytest]\n")
    junit = repo / "junit.xml"
    subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                    f"--junitxml={junit}", "tests"], cwd=repo, capture_output=True)
    assert not check.agreed_results(repo, junit)["Thing"]["passed"]
    junit.write_text("<testsuites><testsuite>")
    assert not check.agreed_results(repo, junit)["Thing"]["passed"]
    assert not check.agreed_results(repo, repo / "missing.xml")["Thing"]["passed"]


def test_a_run_counts_for_head_only_if_its_files_were_heads_before_and_after(repo):
    head = check.git(repo, "rev-parse", "HEAD").strip()
    assert check.still_at_revision(repo, head, check.at_revision(repo))[0]
    edit(repo, "src/pkg/mod.py", "1", "2")
    before = check.at_revision(repo)  # dirty when the run starts, restored while it runs
    edit(repo, "src/pkg/mod.py", "2", "1")
    assert not check.still_at_revision(repo, head, before)[0]
    before = check.at_revision(repo)  # clean, then another session commits during the run
    edit(repo, "docs/page.md", "Intro.", "Intro, again.")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "meanwhile")
    assert not check.still_at_revision(repo, head, before)[0]
