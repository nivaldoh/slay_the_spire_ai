"""scripts/check.py's risky-edit warnings and marker list, on a small Git repository.

Each planted edit must print its "needs your yes" line, and an unrelated edit none (light
factory plan, stage 1). Whether check.py's suite counts match plain pytest's was compared by
hand; see the docstring of scripts/check.py for what each warning means.
"""

import importlib.util
import json
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
    "docs/agreed-checks.md": "- Thing: `uv run --locked pytest -ra tests/agreed/test_a.py`.\n"
                             "- Folder: `pytest tests/agreed_dir`.\n",
    "tests/agreed_dir/test_c.py": "def test_c():\n    x = 3\n    assert x == 3\n",
    "tests/agreed/test_a.py": "def test_a():\n    assert 1 == 1\n",
    "tests/other/test_b.py": "import pytest\n\n\ndef test_b():\n    assert 2 == 2\n"
                             "    with pytest.raises(ValueError):\n        int('x')\n",
    "tests/twwarhammer3/prompts/llm.txt": "You command an army.\n",
    "docs/page.md": f"Intro.\n\n{MARK} Thing — Claude, 2026-10-29: X, not Y.\n",
    "src/pkg/mod.py": "def f():\n    return 1\n",
    "uv.lock": LOCK.format("a", "1.0"),
    "tests/plants.toml": "".join(
        f'[[plant]]\nid = "{name}"\nguards = "g"\nfile = "src/pkg/mod.py"\nold = "return 1"\n'
        f'new = "return 2"\ntests = ["{test}"]\n\n'
        for name, test in (("a", "tests/agreed/test_a.py"), ("b", "tests/other/test_b.py"))),
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


def drop_plant_b(root):
    text = (root / "tests/plants.toml").read_text()
    (root / "tests/plants.toml").write_text(text[:text.index('[[plant]]\nid = "b"')])


def swap_plant_tests(root):
    # Each line moves verbatim to the other plant, so a line count would see no change.
    edit(root, "tests/plants.toml", "tests/agreed/test_a.py", "@")
    edit(root, "tests/plants.toml", "tests/other/test_b.py", "tests/agreed/test_a.py")
    edit(root, "tests/plants.toml", "@", "tests/other/test_b.py")


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
    "agreed folder line": (lambda r: edit(r, "tests/agreed_dir/test_c.py", "x = 3", "x = 4"),
                           "an agreed check's files lose or change lines: "
                           "tests/agreed_dir/test_c.py"),
    "skip call": (lambda r: edit(r, "tests/other/test_b.py", "def test_b():\n",
                                 "def test_b():\n    pytest." + "skip('x')\n"),
                  "1 skip or xfail added: tests/other/test_b.py"),
    "snapshot": (lambda r: edit(r, "tests/twwarhammer3/prompts/llm.txt", "army", "host"),
                 "prompt snapshots changed: tests/twwarhammer3/prompts/llm.txt"),
    "lock": (lambda r: (r / "uv.lock").write_text(LOCK.format("a", "1.1") + LOCK.format("b", "2")),
             "uv.lock adds or changes packages: a 1.0 -> 1.1, b new -> 2"),
    "plant weakened": (lambda r: edit(r, "tests/plants.toml", 'new = "return 2"\ntests = ["tests/a',
                                      'new = "return 2"\ntests = ["tests/o'),
                       "planted versions removed or changed (tests/plants.toml; updating one to new"
                       " code counts too): a changed (tests)"),
    "plant removed": (lambda r: drop_plant_b(r),
                      "planted versions removed or changed (tests/plants.toml; updating one to new"
                      " code counts too): b removed"),
    "plants swap tests": (lambda r: swap_plant_tests(r),
        "planted versions removed or changed (tests/plants.toml; updating one to new code counts"
        " too): a changed (tests); b changed (tests)"),
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
    # A new plant needs no yes.
    edit(repo, "tests/plants.toml", '[[plant]]\nid = "a"', '[[plant]]\nid = "c"\nguards = "g"\n'
         'file = "src/pkg/mod.py"\nold = "1"\nnew = "3"\ntests = ["t"]\n\n[[plant]]\nid = "a"')
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


def test_markers_in_the_private_thesis_notes_are_not_listed(repo):
    for name in ("docs/thesis/notes.md", "docs/thesis.md"):
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text(f"This {RESTS} `docs/gone.md` X.\n")
    assert check.marker_problems(repo) == [
        f"docs/thesis.md: {RESTS} docs/gone.md, which does not exist"]


def test_state_md_over_120_lines_is_named(tmp_path):
    assert check.long_pages(tmp_path) == []  # no page: nothing to say, no crash
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/state.md").write_text("x\n" * 120)
    assert check.long_pages(tmp_path) == []
    (tmp_path / "docs/state.md").write_text("x\n" * 121)
    assert check.long_pages(tmp_path) == ["docs/state.md has 121 lines, over 120"]
    (tmp_path / "docs/state.md").write_text("x\n" * 120 + "x")  # no final newline
    assert check.long_pages(tmp_path) == ["docs/state.md has 121 lines, over 120"]


def test_a_run_in_a_linked_worktree_says_so_and_keeps_its_exit_code(
        repo, tmp_path_factory, monkeypatch, capsys):
    assert check.linked_worktree(repo) == []  # the main checkout
    linked = tmp_path_factory.mktemp("sibling") / "linked"  # beside it, as worktrees are here
    git(repo, "worktree", "add", "-q", str(linked))
    (linked / "pytest.ini").write_text("[pytest]\n")
    (linked / "ruff.toml").write_text('[lint]\nselect = ["F"]\n')
    (linked / "docs/state.md").write_text("# Project state\n")
    assert run_main(linked, monkeypatch) == 0
    assert (f"\nworktree  a linked worktree of {repo.resolve()}: tests that read its runs/ "
            "evidence can skip here") in capsys.readouterr().out


def test_replayed_plants_are_caught_missed_stale_hung_or_lack_a_baseline(tmp_path, monkeypatch):
    (tmp_path / "src/pkg").mkdir(parents=True)
    (tmp_path / "src/pkg/mod.py").write_text("def f():\n    return 1\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_m.py").write_text("from pkg.mod import f\n\n\ndef test_f():\n"
                                              "    assert f() == 1\n")
    (tmp_path / "tests/test_bad.py").write_text("def test_bad():\n    assert 1 == 2\n")
    (tmp_path / "tests/test_skipped.py").write_text(f"import pytest\n\n\n{SKIP}\n"
                                                    "def test_s():\n    assert 1 == 1\n")
    (tmp_path / "pytest.ini").write_text("[pytest]\n")
    # A stand-in for the stale-plant rule, which fails whenever any plant is applied.
    (tmp_path / "tests/test_check_script.py").write_text(
        "from pathlib import Path\n\n\ndef test_other():\n    assert True\n\n\n"
        f"def {check.STALE_RULE.split('::')[1]}():\n"
        "    assert 'def f():' in Path('src/pkg/mod.py').read_text()\n")

    def plant(name, old, new, tests=("tests/test_m.py",)):
        return (f'[[plant]]\nid = "{name}"\nguards = "g"\nfile = "src/pkg/mod.py"\n'
                f"old = {json.dumps(old)}\nnew = {json.dumps(new)}\ntests = {json.dumps(tests)}\n")
    (tmp_path / "tests/plants.toml").write_text("".join([
        plant("caught", "return 1", "return 2"),
        # Ends pytest before it writes its report, right after "caught" wrote a failing one.
        plant("no-report", "def f():", "import os\nos._exit(0)\n\n\ndef f():"),
        plant("missed", "def f():", "def f(x=0):"),
        plant("only-the-stale-rule-fails", "def f():", "def f(y=0):",
              ("tests/test_check_script.py",)),
        plant("stale", "return 3", "return 4"),
        plant("hang", "    return 1", "    while True:\n        pass"),
        plant("no-baseline", "return 1", "return 2", ("tests/test_bad.py",)),
        plant("all-skipped", "return 1", "return 2", ("tests/test_skipped.py",)),
    ]))
    monkeypatch.setattr(check, "PLANT_TIMEOUT_S", 5)
    report = check.replay_plants(tmp_path)
    assert [verdict for verdict, _, _ in report] == [
        "caught", "NOREPORT", "MISSED", "MISSED", "stale", "HANG", "baseline", "baseline"]
    assert report[0][1] == "caught: tests.test_m.test_f"
    assert (tmp_path / "src/pkg/mod.py").read_text() == "def f():\n    return 1\n"


def test_an_interrupted_plant_run_leaves_no_tests_running(tmp_path, monkeypatch):
    (tmp_path / "tests").mkdir()
    # A bounded sleep: if the kill is ever wrong, the child still ends by itself.
    (tmp_path / "tests/test_hang.py").write_text(
        "def test_h():\n    import time\n    time.sleep(20)\n")
    started = []

    class Interrupted(subprocess.Popen):
        def communicate(self, *args, timeout=None, **kwargs):
            started.append(self)
            if timeout:  # Ctrl-C arrives while the tests run
                raise KeyboardInterrupt
            return super().communicate(*args, **kwargs)

    monkeypatch.setattr(check.subprocess, "Popen", Interrupted)
    with pytest.raises(KeyboardInterrupt):
        check.plant_tests(tmp_path, ["tests/test_hang.py"], tmp_path / "j.xml")
    assert started[0].poll() is not None  # killed and reaped
    assert started[0].returncode == -check.signal.SIGKILL  # not waited for until it ended


def test_each_committed_plant_still_applies_and_names_real_tests():
    root = Path(check.__file__).resolve().parents[1]
    plants = check.plant_list(root)
    ids = [plant["id"] for plant in plants]
    assert plants and len(ids) == len(set(ids))
    # A plant whose text is gone: update `old`/`new` to the same wrong version of the new code.
    assert check.stale_plants(root) == []
    assert all(plant["old"] != plant["new"] and plant["guards"] and plant["tests"]
               and all((root / test.split("::")[0]).exists() for test in plant["tests"])
               for plant in plants)


def run_main(root, monkeypatch, *args):
    monkeypatch.setattr(check, "ROOT", root)
    monkeypatch.setattr(sys, "argv", ["check.py", *args])
    monkeypatch.setattr(check.signal, "signal", lambda *a: None)  # plants_main's SIGTERM handler
    return check.main()


@pytest.mark.parametrize("change,code", [
    (None, 0),
    (("tests/agreed/test_a.py", "1 == 1", "1 == 2"), 1),
    (("src/pkg/mod.py", "def f", "import os\n\n\ndef f"), 1),
])
def test_check_exits_1_when_ruff_or_a_test_fails(repo, monkeypatch, capsys, change, code):
    (repo / "pytest.ini").write_text("[pytest]\n")
    (repo / "ruff.toml").write_text('[lint]\nselect = ["F"]\n')  # not Ruff's defaults
    (repo / ".gitignore").write_text("runs/\n")
    (repo / "docs/state.md").write_text("x\n" * 121)  # a warning, which never fails the run
    (repo / "tests/other/test_env.py").write_text(
        "import os\n\n\ndef test_env():\n    assert 'WH3_WRITE_PROMPTS' not in os.environ\n")
    monkeypatch.setenv("WH3_WRITE_PROMPTS", "1")
    if change:
        edit(repo, *change)
    assert run_main(repo, monkeypatch) == code
    assert "\npages     docs/state.md has 121 lines, over 120" in capsys.readouterr().out


def test_plants_exits_1_on_a_missed_plant(repo, monkeypatch):
    (repo / "src/gameai").mkdir()
    (repo / "src/gameai/__init__.py").write_text("")
    (repo / "pytest.ini").write_text("[pytest]\n")
    (repo / ".gitignore").write_text("runs/\n")
    git(repo, "add", ".")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "gameai")
    assert run_main(repo, monkeypatch, "--plants") == 1  # neither test calls f
    for name in ("tests/agreed/test_a.py", "tests/other/test_b.py"):
        (repo / name).write_text("from pkg.mod import f\n\n\ndef test_f():\n    assert f() == 1\n")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "caught")
    assert run_main(repo, monkeypatch, "--plants") == 0
