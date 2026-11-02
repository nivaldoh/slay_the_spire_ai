"""scripts/check.py's risky-edit warnings and marker list, on a small Git repository.

Each planted edit must print its "needs your yes" line, and an unrelated edit none (light
factory plan, stage 1). Whether check.py's suite counts match plain pytest's was compared by
hand; see the docstring of scripts/check.py for what each warning means.
"""

import hashlib
import importlib.util
import json
import os
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


def test_a_marker_in_log_history_is_listed(repo):
    (repo / "docs/wh3").mkdir(parents=True)
    (repo / "docs/wh3/log.md").write_text(
        f"## 2026-10-23\n\n{MARK} night cap $5 (assistant, 2026-10-23).\n"
        f"The `{MARK}` mention and a retired choice stay as history.\n")
    (repo / "docs/backlog.md").write_text(f"{MARK} a plan, not history (Claude, 2026-10-30).\n")
    assert check.marker_problems(repo) == ["docs/wh3/log.md:3: a marker in log history"]


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
    (linked / "runs/twwarhammer3").mkdir(parents=True)  # e.g. a pack built here: still less
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


def test_planted_tests_keep_their_scratch_in_runs(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_where.py").write_text(
        "def test_where(tmp_path):\n    open('where.txt', 'w').write(str(tmp_path))\n")
    check.plant_tests(tmp_path, ["tests/test_where.py"], tmp_path / "j.xml")
    where = Path((tmp_path / "where.txt").read_text())
    assert where.is_relative_to(tmp_path / "runs/test-scratch")  # not /tmp: a leak stays findable


def test_an_interrupted_plant_run_leaves_no_tests_running(tmp_path, monkeypatch):
    (tmp_path / "tests").mkdir()
    # A bounded sleep: if the kill is ever wrong, the child still ends by itself.
    (tmp_path / "tests/test_hang.py").write_text(
        "def test_h():\n    import time\n    time.sleep(5)\n")
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
    # pytest cannot collect it (exit 2), and Ruff finds nothing to say
    (("tests/other/test_b.py", "import pytest", "import pytest\nraise ImportError('x')"), 1),
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


def test_a_plant_replays_on_a_copy_of_the_saved_evidence_it_names(repo, monkeypatch):
    (repo / "src/gameai").mkdir()
    (repo / "src/gameai/__init__.py").write_text("")
    (repo / "pytest.ini").write_text("[pytest]\n")
    (repo / ".gitignore").write_text("runs/\n")
    (repo / "runs/ev").mkdir(parents=True)  # ignored, as real evidence is
    (repo / "runs/ev/expected.txt").write_text("1\n")
    (repo / "tests/agreed/test_a.py").write_text(
        "from pathlib import Path\n\nimport pytest\n\nfrom pkg.mod import f\n\n\ndef test_f():\n"
        "    if not Path('runs/ev/expected.txt').exists():\n"
        "        pytest." + "skip('needs the saved evidence')\n"
        "    assert f() == int(Path('runs/ev/expected.txt').read_text())\n")
    (repo / "tests/plants.toml").write_text(
        '[[plant]]\nid = "a"\nguards = "g"\nfile = "src/pkg/mod.py"\nold = "return 1"\n'
        'new = "return 2"\ntests = ["tests/agreed/test_a.py"]\nevidence = ["runs/ev"]\n')
    git(repo, "add", ".")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "evidence")
    assert run_main(repo, monkeypatch, "--plants") == 0  # caught on the copy
    assert (repo / "runs/ev/expected.txt").read_text() == "1\n"  # the original is untouched


def test_a_pass_records_the_tree_it_checked_and_a_failure_clears_it(repo, monkeypatch):
    (repo / "pytest.ini").write_text("[pytest]\n")
    (repo / "ruff.toml").write_text('[lint]\nselect = ["F"]\n')
    # What a run leaves behind is ignored, as in the repository's own .gitignore
    (repo / ".gitignore").write_text("runs/\n__pycache__/\n.pytest_cache/\n.ruff_cache/\n")
    (repo / "docs/state.md").write_text("# Project state\n")
    assert run_main(repo, monkeypatch) == 0
    record = json.loads((repo / "runs/checks/last-pass.json").read_text())
    assert record["tree"] == check.tree_content(repo)
    # A new size: a same-size edit within the same second can rerun the cached bytecode
    edit(repo, "tests/agreed/test_a.py", "1 == 1", "1 == 1 + 1")
    assert run_main(repo, monkeypatch) == 1
    assert not (repo / "runs/checks/last-pass.json").exists()


def test_the_checked_tree_ignores_staging_and_commits_but_not_edits(repo):
    base = check.tree_content(repo)
    (repo / "new.txt").write_text("x\n")
    added = check.tree_content(repo)
    assert added != base  # a new untracked file counts
    git(repo, "add", "new.txt")
    assert check.tree_content(repo) == added  # staging changes no file
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "new")
    assert check.tree_content(repo) == added  # nor does a commit
    edit(repo, "src/pkg/mod.py", "return 1", "return 3")
    assert check.tree_content(repo) != added
    (repo / "new.txt").unlink()
    assert check.tree_content(repo) not in (base, added)



def test_a_tree_that_changes_during_the_run_gets_no_record(repo, monkeypatch, capsys):
    (repo / "pytest.ini").write_text("[pytest]\n")
    (repo / "ruff.toml").write_text('[lint]\nselect = ["F"]\n')
    (repo / ".gitignore").write_text("runs/\n__pycache__/\n.pytest_cache/\n.ruff_cache/\n")
    (repo / "docs/state.md").write_text("# Project state\n")
    (repo / "tests/other/test_writes.py").write_text(  # another writer edits the tree meanwhile
        "from pathlib import Path\n\n\ndef test_w():\n    Path('notes.txt').write_text('new')\n")
    assert run_main(repo, monkeypatch) == 0
    assert not (repo / "runs/checks/last-pass.json").exists()
    assert "\nrecord    none: files changed while it ran" in capsys.readouterr().out


def test_the_checked_tree_keeps_staged_deletions_and_skips_only_the_thesis_notes(repo):
    (repo / "docs/page.md").unlink()
    deleted = check.tree_content(repo)
    git(repo, "rm", "-q", "--cached", "docs/page.md")
    assert check.tree_content(repo) == deleted  # staging the deletion changes no file
    (repo / "docs/thesis").mkdir()
    (repo / "docs/thesis/notes.md").write_text("the owner's untracked note\n")
    assert check.tree_content(repo) == deleted  # left out
    (repo / "docs/new.md").write_text("A new page.\n")
    assert check.tree_content(repo) != deleted  # other docs count, untracked or not
    (repo / "docs/new.md").unlink()
    (repo / "configs").mkdir()
    (repo / "configs/new_prompt.md").write_text("A new prompt.\n")
    prompt = check.tree_content(repo)
    assert prompt != deleted  # any other untracked file counts, Markdown included
    git(repo, "add", "configs/new_prompt.md")
    assert check.tree_content(repo) == prompt  # and staging it changes nothing
    (repo / "src/pkg/mod.py").rename(repo / "src/pkg/moved.py")
    renamed = check.tree_content(repo)
    git(repo, "add", "-A", "src")
    assert check.tree_content(repo) == renamed != prompt


@pytest.mark.parametrize("failure", ["early-git-error", "interrupted", "invalid-base"])
def test_an_aborted_check_clears_the_previous_pass(repo, monkeypatch, failure):
    (repo / "pytest.ini").write_text("[pytest]\n")
    (repo / "ruff.toml").write_text('[lint]\nselect = ["F"]\n')
    (repo / ".gitignore").write_text("runs/\n__pycache__/\n.pytest_cache/\n.ruff_cache/\n")
    (repo / "docs/state.md").write_text("# Project state\n")
    record = repo / "runs/checks/last-pass.json"
    record.parent.mkdir(parents=True)
    content = check.tree_content(repo)
    record.write_text(json.dumps({"tree": content}))
    if failure != "invalid-base":
        original = check.git

        def abort(root, *args):
            if args == ("rev-parse", "--short", "HEAD"):
                if failure == "interrupted":
                    raise KeyboardInterrupt
                raise subprocess.CalledProcessError(128, ["git", *args])
            return original(root, *args)

        monkeypatch.setattr(check, "git", abort)
    error = KeyboardInterrupt if failure == "interrupted" else subprocess.CalledProcessError
    with pytest.raises(error):
        run_main(repo, monkeypatch, "--base", "missing-abort-regression-revision")
    assert check.tree_content(repo) == content  # the previous record would still match
    assert not record.exists()


@pytest.mark.parametrize("option", ["--help", "--plants"])
def test_help_and_plants_leave_the_normal_check_record_alone(repo, monkeypatch, option):
    record = repo / "runs/checks/last-pass.json"
    record.parent.mkdir(parents=True)
    previous = '{"tree": "previous normal check"}\n'
    record.write_text(previous)
    monkeypatch.setattr(check, "plants_main", lambda: 0)
    if option == "--help":
        with pytest.raises(SystemExit) as stopped:
            run_main(repo, monkeypatch, option)
        assert stopped.value.code == 0
    else:
        assert run_main(repo, monkeypatch, option) == 0
    assert record.read_text() == previous


@pytest.mark.parametrize("args", [("--base",), ("--unknown-check-option",)])
def test_invalid_check_arguments_clear_the_previous_pass(repo, monkeypatch, args):
    (repo / ".gitignore").write_text("runs/\n")
    record = repo / "runs/checks/last-pass.json"
    record.parent.mkdir(parents=True)
    content = check.tree_content(repo)
    record.write_text(json.dumps({"tree": content}))
    with pytest.raises(SystemExit) as stopped:
        run_main(repo, monkeypatch, *args)
    assert stopped.value.code == 2
    assert check.tree_content(repo) == content
    assert not record.exists()


@pytest.mark.parametrize("target_kind", ["directory", "dangling", "file"])
def test_the_checked_tree_hashes_symlink_targets(repo, target_kind):
    if target_kind == "directory":
        (repo / "a").mkdir()
        (repo / "b").mkdir()
    elif target_kind == "file":
        (repo / "a").write_text("same contents\n")
        (repo / "b").write_text("same contents\n")
    link = repo / "link"
    link.symlink_to("a", target_is_directory=target_kind == "directory")
    before = check.tree_content(repo)
    link.unlink()
    link.symlink_to("b", target_is_directory=target_kind == "directory")
    after = check.tree_content(repo)
    assert after != before
    git(repo, "add", "link")
    assert check.tree_content(repo) == after
    link.unlink()
    assert check.tree_content(repo) not in (before, after)


def test_the_checked_tree_distinguishes_a_symlink_from_its_target_text(repo):
    link = repo / "link"
    link.symlink_to("missing-target")
    before = check.tree_content(repo)
    link.unlink()
    link.write_text("missing-target")
    assert check.tree_content(repo) != before


@pytest.mark.parametrize("changed", ["source", "test"])
@pytest.mark.parametrize("shared_prefix", [False, True])
def test_normal_check_reads_same_size_same_timestamp_edits(
        repo, monkeypatch, changed, shared_prefix):
    (repo / "pytest.ini").write_text("[pytest]\n")
    (repo / "ruff.toml").write_text('[lint]\nselect = ["F"]\n')
    (repo / ".gitignore").write_text("runs/\n__pycache__/\n.pytest_cache/\n.ruff_cache/\n")
    (repo / "docs/state.md").write_text("# Project state\n")
    (repo / "runs").mkdir()
    (repo / "thing.py").write_text("VALUE = 1\n")
    test = repo / "tests/test_bytecode.py"
    test.write_text("import sys\nfrom pathlib import Path\n\nfrom thing import VALUE\n\n\n"
                    "def test_value():\n"
                    "    Path('runs/pytest-prefix.txt').write_text(sys.pycache_prefix or '')\n"
                    "    assert VALUE == 1\n")
    monkeypatch.delenv("PYTHONDONTWRITEBYTECODE", raising=False)
    monkeypatch.delenv("PYTHONPYCACHEPREFIX", raising=False)
    if shared_prefix:
        monkeypatch.setenv("PYTHONPYCACHEPREFIX", str(repo / "runs/shared-bytecode"))
    inherited = os.environ.get("PYTHONPYCACHEPREFIX")
    seeded = subprocess.run([sys.executable, "-m", "pytest", "-q", str(test)], cwd=repo,
                            capture_output=True, text=True)
    assert seeded.returncode == 0, seeded.stdout + seeded.stderr
    caches = {path: (path.stat().st_mtime_ns, path.read_bytes())
              for path in repo.rglob("*.pyc")
              if path.name.startswith(("thing.", "test_bytecode."))}
    assert len(caches) == 2  # a normal module and pytest's rewritten test
    target = repo / "thing.py" if changed == "source" else test
    before = target.stat()
    good = target.read_text()
    bad = good.replace("= 1" if changed == "source" else "== 1",
                       "= 2" if changed == "source" else "== 2")
    assert good != bad and len(good.encode()) == len(bad.encode())
    target.write_text(bad)
    os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
    assert target.stat().st_size == before.st_size
    assert target.stat().st_mtime_ns == before.st_mtime_ns
    assert run_main(repo, monkeypatch) == 1
    assert not (repo / "runs/checks/last-pass.json").exists()
    used = Path((repo / "runs/pytest-prefix.txt").read_text())
    assert used.parent == repo / "runs/test-scratch"
    assert not used.exists()  # failure also removes the disposable bytecode tree
    assert os.environ.get("PYTHONPYCACHEPREFIX") == inherited
    assert {path: (path.stat().st_mtime_ns, path.read_bytes()) for path in caches} == caches


def test_normal_check_cleans_its_bytecode_prefix_after_interruption(repo, monkeypatch):
    original, prefixes = check.subprocess.run, []

    def interrupted(command, **kwargs):
        if command[:3] == [sys.executable, "-m", "pytest"]:
            prefix = kwargs["env"].get("PYTHONPYCACHEPREFIX")
            if prefix:
                prefixes.append(Path(prefix))
            raise KeyboardInterrupt
        return original(command, **kwargs)

    monkeypatch.setattr(check.subprocess, "run", interrupted)
    with pytest.raises(KeyboardInterrupt):
        run_main(repo, monkeypatch)
    assert len(prefixes) == 1
    assert prefixes[0].parent == repo / "runs/test-scratch"
    assert not prefixes[0].exists()
    assert not (repo / "runs/checks/last-pass.json").exists()


@pytest.mark.parametrize("key,value", [
    ("PYTEST_ADDOPTS", "-k test_pass"),
    ("PYTEST_ADDOPTS", "tests/test_pass.py"),
    ("PYTHONOPTIMIZE", "1"),
])
def test_normal_check_ignores_caller_selection_and_optimization(
        repo, monkeypatch, capsys, key, value):
    (repo / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n")
    (repo / "ruff.toml").write_text('[lint]\nselect = ["F"]\n')
    (repo / ".gitignore").write_text("runs/\n__pycache__/\n.pytest_cache/\n.ruff_cache/\n")
    (repo / "docs/state.md").write_text("# Project state\n")
    (repo / "docs/agreed-checks.md").write_text("- Whole suite: `pytest tests`.\n")
    if key == "PYTEST_ADDOPTS":
        (repo / "tests/test_pass.py").write_text("def test_pass():\n    assert 1 == 1\n")
        (repo / "tests/test_fail.py").write_text("def test_fail():\n    assert 1 == 2\n")
        failed = "test_fail"
    else:
        (repo / "helper.py").write_text("def reject():\n    assert False, 'must reject'\n")
        (repo / "tests/test_helper.py").write_text(
            "from helper import reject\n\n\ndef test_helper():\n    reject()\n")
        failed = "test_helper"
    monkeypatch.delenv("PYTEST_ADDOPTS", raising=False)
    monkeypatch.delenv("PYTHONOPTIMIZE", raising=False)
    monkeypatch.setenv(key, value)
    monkeypatch.setenv("WH3_WRITE_PROMPTS", "1")
    parent = {name: os.environ.get(name)
              for name in ("PYTEST_ADDOPTS", "PYTHONOPTIMIZE", "WH3_WRITE_PROMPTS")}
    assert run_main(repo, monkeypatch) == 1
    assert f"FAILED tests/{failed}.py::{failed}" in capsys.readouterr().out
    assert not (repo / "runs/checks/last-pass.json").exists()
    result = json.loads((repo / "runs/checks/agreed-passes.jsonl").read_text().splitlines()[-1])
    assert not result["checks"]["Whole suite"]["passed"]
    assert {name: os.environ.get(name) for name in parent} == parent


@pytest.mark.parametrize("mode", ["early-exit", "stale-report", "collect-only", "all-skipped",
                                 "collection-error", "failed-report"])
def test_normal_check_requires_a_completed_test_report(repo, monkeypatch, capsys, mode):
    # pytest-dev/pytest src/_pytest/junitxml.py: the JUnit report is written at session finish.
    # Exiting an imported module with status 0 never reaches that hook.
    (repo / "pytest.ini").write_text("[pytest]\npython_files = test_completion.py\n")
    (repo / "ruff.toml").write_text('[lint]\nselect = ["F"]\n')
    (repo / ".gitignore").write_text("runs/\n__pycache__/\n.pytest_cache/\n.ruff_cache/\n")
    (repo / "docs/state.md").write_text("# Project state\n")
    (repo / "docs/agreed-checks.md").write_text(
        "- Completion: `pytest tests/test_completion.py::test_completion`.\n"
        "- File: `pytest tests/test_completion.py`.\n")
    target = repo / "tests/test_completion.py"
    target.write_text("def test_completion():\n    assert True\n")
    if mode == "stale-report":
        # Same path as this process's normal gate: a prior interrupted run could leave it.
        junit = repo / "runs/test-scratch" / f"check-{os.getpid()}.xml"
        junit.parent.mkdir(parents=True)
        seeded = subprocess.run([sys.executable, "-m", "pytest", "-q", f"--junitxml={junit}"],
                                cwd=repo, capture_output=True, text=True)
        assert seeded.returncode == 0, seeded.stdout + seeded.stderr
        assert check.agreed_results(repo, junit)["Completion"]["passed"]
    if mode in ("early-exit", "stale-report"):
        target.write_text("import os\nos._exit(0)\n")
    elif mode == "collect-only":
        (repo / "pytest.ini").write_text(
            "[pytest]\npython_files = test_completion.py\naddopts = --collect-only\n")
    elif mode == "collection-error":
        target.write_text("raise RuntimeError('collection failure')\n")
        (repo / "conftest.py").write_text(
            "import pytest\n\n\ndef pytest_collection_finish():\n"
            "    pytest.exit('collection stopped', returncode=0)\n")
    elif mode == "failed-report":
        target.write_text("def test_completion():\n    assert True\n\n\n"
                          "def test_failure():\n    assert False\n")
        (repo / "conftest.py").write_text(
            "def pytest_sessionfinish(session):\n    session.exitstatus = 0\n")
    else:
        target.write_text("import pytest\n\n\ndef test_completion():\n"
                          "    pytest.skip('unavailable fixture')\n")
    assert run_main(repo, monkeypatch) == 1
    assert "pytest completion evidence missing" in capsys.readouterr().out
    assert not (repo / check.CHECKED).exists()
    result = json.loads((repo / check.PASSES).read_text().splitlines()[-1])
    assert set(result["checks"]) == {"Completion", "File"}
    assert all(not row["passed"] for row in result["checks"].values())


def test_normal_check_accepts_a_completed_test_report(repo, monkeypatch, capsys):
    (repo / "pytest.ini").write_text("[pytest]\n")
    (repo / "ruff.toml").write_text('[lint]\nselect = ["F"]\n')
    (repo / ".gitignore").write_text("runs/\n__pycache__/\n.pytest_cache/\n.ruff_cache/\n")
    (repo / "docs/state.md").write_text("# Project state\n")
    assert run_main(repo, monkeypatch) == 0
    assert "pytest completion evidence missing" not in capsys.readouterr().out
    assert json.loads((repo / check.CHECKED).read_text())["tree"] == check.tree_content(repo)
    result = json.loads((repo / check.PASSES).read_text().splitlines()[-1])
    assert set(result["checks"]) == {"Thing", "Folder"}
    assert all(row["passed"] for row in result["checks"].values())


def test_a_needs_your_yes_item_is_printed_once_and_logged_every_run(repo, monkeypatch, capsys):
    (repo / "pytest.ini").write_text("[pytest]\n")
    (repo / "ruff.toml").write_text('[lint]\nselect = ["F"]\n')
    (repo / ".gitignore").write_text("runs/\n")
    PLANTED["skip"][0](repo)
    item = PLANTED["skip"][1]
    assert run_main(repo, monkeypatch, "--base", "HEAD") == 0
    assert f"  - {item}" in capsys.readouterr().out
    assert run_main(repo, monkeypatch, "--base", "HEAD") == 0
    out = capsys.readouterr().out
    assert f"  - {item}" not in out and "  - and 1 printed by an earlier run" in out
    log = sorted((repo / "runs/checks").glob("*.log"))[-1].read_text()
    assert f"== needs your yes, every item\n{item}" in log
    PLANTED["xfail"][0](repo)  # a new item is printed; the old one stays a count
    assert run_main(repo, monkeypatch, "--base", "HEAD") == 0
    out = capsys.readouterr().out
    assert "  - 2 skip or xfail added" in out and "  - and" not in out


def test_a_run_removes_the_scratch_of_ended_runs_and_keeps_a_running_ones(repo, monkeypatch):
    (repo / "pytest.ini").write_text("[pytest]\n")
    (repo / "ruff.toml").write_text('[lint]\nselect = ["F"]\n')
    (repo / ".gitignore").write_text("runs/\n")
    scratch = repo / "runs/test-scratch"
    ended, running = scratch / "check-999999999", scratch / f"check-{os.getppid()}"
    for folder in (ended, running):
        (folder / "test_x0").mkdir(parents=True)
    (scratch / "check-999999999.xml").write_text("<testsuites/>")
    assert run_main(repo, monkeypatch) == 0
    assert not ended.exists() and not (scratch / "check-999999999.xml").exists()
    assert running.exists()


def test_warning_cache_write_failure_cannot_block_passing_checks(repo, monkeypatch, capsys):
    (repo / "pytest.ini").write_text("[pytest]\n")
    (repo / "ruff.toml").write_text('[lint]\nselect = ["F"]\n')
    (repo / ".gitignore").write_text("runs/\n")
    PLANTED["skip"][0](repo)
    item = PLANTED["skip"][1]
    # A directory is unreadable as JSON and cannot be overwritten as a cache file;
    # the rest of runs/checks remains writable for the actual gate log and receipt.
    (repo / check.YES_SHOWN).mkdir(parents=True)

    assert run_main(repo, monkeypatch, "--base", "HEAD") == 0

    out = capsys.readouterr().out
    assert "result    PASSED: Ruff clean" in out and f"  - {item}" in out
    log = next((repo / "runs/checks").glob("*.log")).read_text()
    assert f"== needs your yes, every item\n{item}" in log
    record = json.loads((repo / check.CHECKED).read_text())
    assert record["tree"] == check.tree_content(repo)


# The "How the code works" flags (check.py's diagram_flags; plan docs/how-code-works-plan.md
# section 6). A view file is JSON inside the page's call, as the page's view files are.
def view_file(view):
    return f'"use strict";\n// a view\nDIAGRAM.tabs.push({json.dumps(view, indent=1)});\n'


def commit_all(root, message):
    git(root, "add", "-A")
    git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", message)
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, check=True,
                          capture_output=True, text=True).stdout.strip()


def test_diagram_flags_follow_the_cited_text_not_its_line_numbers(tmp_path):
    git(tmp_path, "init", "-q")
    (tmp_path / "src/pkg").mkdir(parents=True)
    code = tmp_path / "src/pkg/mod.py"
    code.write_text("def f():\n    return 1\n")
    cited = commit_all(tmp_path, "code")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/how-code-works-view-s.js").write_text(view_file({
        "id": "s", "commit": cited, "reviewed": "2026-11-01",
        "elements": [{"id": "a", "refs": ["src/pkg/mod.py:1-2", "runs/local/evidence.txt"]}]}))
    # An unknown commit or a range past the end cannot be read; an item's own commit wins.
    (tmp_path / "docs/how-code-works-view-t.js").write_text(view_file({
        "id": "t", "commit": "0000000", "reviewed": "2026-11-01",
        "elements": [{"id": "x", "refs": ["src/pkg/mod.py:1"]},
                     {"id": "y", "commit": cited, "refs": ["src/pkg/mod.py:1-2"]},
                     {"id": "z", "commit": cited, "refs": ["src/pkg/mod.py:9"]}]}))
    commit_all(tmp_path, "views")
    flags = lambda: check.diagram_flags(tmp_path, today="2026-11-02")["views"]  # noqa: E731
    assert flags()["s"] == {"flagged": False, "reasons": [], "moved": {}, "example_changed": []}
    assert flags()["t"]["reasons"] == ["cannot read src/pkg/mod.py:1 at 0000000",
                                       f"cannot read src/pkg/mod.py:9 at {cited}"]
    code.write_text("import os\n\n\ndef f():\n    return 1\n")  # moved, not changed
    commit_all(tmp_path, "move")
    moved = flags()["s"]
    assert not moved["flagged"] and moved["moved"] == {"src/pkg/mod.py:1-2": "src/pkg/mod.py:4-5"}
    code.write_text("import os\n\n\ndef f():\n    return 2\n")
    commit_all(tmp_path, "change")
    assert flags()["s"]["reasons"] == [f"src/pkg/mod.py:1-2 changed since {cited}"]
    code.unlink()
    commit_all(tmp_path, "remove")
    assert flags()["s"]["reasons"] == [f"src/pkg/mod.py is gone (cited at {cited})"]
    # A card's refs, a status's refs ({text, refs}) and the refs of the boxes an example generated
    # for the view (view.generated) and of that graph itself count as cited too.
    other = tmp_path / "src/pkg/other.py"
    other.write_text("a = 1\nb = 2\nc = 3\nd = 4\n")
    later = commit_all(tmp_path, "other")
    (tmp_path / "docs/how-code-works-view-c.js").write_text(view_file({
        "id": "c", "commit": later, "reviewed": "2026-11-01",
        "cards": {"k": {"refs": ["src/pkg/other.py:1"]}},
        "elements": [{"id": "b", "status": {"text": "x", "refs": ["src/pkg/other.py:2"]}}],
        "generated": {"example": "made", "key": "graph"}}))
    made = {"made": {"graph": {"elements": [{"id": "m", "refs": ["src/pkg/other.py:3"]}],
                               "refs": ["src/pkg/other.py:4"]}}}
    (tmp_path / "docs/how-code-works-example-made.js").write_text(
        f"// an example\nObject.assign(DIAGRAM_EXAMPLES, {json.dumps(made)});\n")
    commit_all(tmp_path, "cards")
    assert flags()["c"]["reasons"] == []
    other.write_text("a = 10\nb = 20\nc = 30\nd = 40\n")
    commit_all(tmp_path, "change other")
    assert flags()["c"]["reasons"] == [f"src/pkg/other.py:{n} changed since {later}"
                                       for n in (1, 2, 3, 4)]


def test_diagram_flags_check_the_file_lists_stated_facts_and_review_age(tmp_path):
    git(tmp_path, "init", "-q")
    files = {
        "src/pkg/a.py": "", "src/pkg/b.py": "", "src/pkg/__init__.py": "",
        "src/other/c.py": "", "scripts/other.py": "",  # another game's: the map leaves them out
        "src/gameai/providers.py": 'PROVIDERS = {"openai": A, "openrouter": B}\n',
        "src/twwarhammer3/protocol.py": 'HIDDEN_KEYS = ("evaluation", "final")\n',
        "docs/twwarhammer3/README.md": "## Code map\n\n- `src/pkg/a.py`: does a,\n"
                                       "  over two lines\n"
                                       "- `src/gameai/providers.py`: routes\n"
                                       "- `src/twwarhammer3/protocol.py`: the protocol\n"
                                       "- `src/old.py`: gone\n"
                                       "- `scripts/other.py`: the other game's\n"
                                       "- `src/other/gone.py`: listed, left out, deleted\n\n"
                                       "## Commands\n\n"
                                       "- `--show`: not a file list line\n",
    }
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
    commit = commit_all(tmp_path, "code")
    owned = ["src/pkg/", "src/gameai/", "src/old.py"]
    digest = lambda text: hashlib.sha256(text.encode()).hexdigest()  # noqa: E731
    views = [
        {"id": "map", "commit": commit, "reviewed": "2026-07-01",
         "facts": {"providers": ["openai", "openrouter", "anthropic"]},
         "outside": ["src/other/", "scripts/other.py"],
         "elements": [{"id": "m.box", "files": owned}]},
        {"id": "s", "commit": commit, "reviewed": "2026-10-30", "example": "e",
         "facts": {"hidden_keys": ["final", "evaluation"]}, "elements": []},
        {"id": "u", "commit": commit, "reviewed": "2026-10-30",
         "facts": {"providers": ["openai"], "hidden_keys": ["final"]}, "elements": []}]
    for view in views:
        (tmp_path / f"docs/how-code-works-view-{view['id']}.js").write_text(view_file(view))
    example = {"e": {"files": {"src/pkg/a.py": digest(""), "src/pkg/b.py": digest("old")},
                     "changed_since": ["src/pkg/b.py"]}}
    (tmp_path / "docs/how-code-works-example-e.js").write_text(
        f"// an example\nObject.assign(DIAGRAM_EXAMPLES, {json.dumps(example)});\n")
    commit_all(tmp_path, "views")
    flags = lambda: check.diagram_flags(tmp_path, today="2026-11-01")["views"]  # noqa: E731
    assert flags()["s"] == {"flagged": False, "reasons": [], "moved": {},
                            "example_changed": ["src/pkg/b.py"]}
    assert flags()["map"]["reasons"] == [
        "not reviewed since 2026-07-01, over three months",
        "src/gameai/providers.py PROVIDERS is now ['openai', 'openrouter']; the view says "
        "['anthropic', 'openai', 'openrouter']",
        "1 src/ Python files missing from the file lists: src/pkg/b.py",
        "1 listed paths in no map box: src/twwarhammer3/protocol.py",
        "2 listed paths not in the repo: src/old.py, src/other/gone.py"]  # outside still checked
    assert flags()["u"]["reasons"] == [  # a view that says less than the code is flagged too
        "src/gameai/providers.py PROVIDERS is now ['openai', 'openrouter']; the view says "
        "['openai']",
        "src/twwarhammer3/protocol.py HIDDEN_KEYS is now ['evaluation', 'final']; the view says "
        "['final']"]
    (tmp_path / "src/pkg/a.py").write_text("x = 1\n")  # changed after the example was made
    commit_all(tmp_path, "change a")
    assert flags()["s"]["reasons"] == ["example e: src/pkg/a.py changed since the example was made"]
    # Four more facts (versions with their values), a list of examples, and story steps that
    # must name ids the view draws, an example generated or its flow's lanes hold.
    battle = "src/twwarhammer3/battle/"
    code = {f"{battle}controllers.py": 'MODEL_PROMPTS = {"llm": llm.PATH, "commander": PROMPT}\n'
                                       'VERSIONS = {"llm": "v22", "commander": "v8"}\n',
            f"{battle}scripted.py": 'POLICIES = {"hold": Hold, "attack_nearest": Nearest}\n',
            f"{battle}graph_author.py": 'DESCRIPTIONS = {"owned": "x", "engage": "y"}\n'}
    for name, text in code.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
    stated = {"model_policies": ["llm", "commander"], "graph_ops": ["owned", "engage"],
              "scripted_policies": ["hold", "attack_nearest"],
              "versions": {"llm": "v22", "commander": "v8"}}
    steps = [{"box": "cav.own", "dots": [["author>cav", "~cav>own"]],
              "rows": ["basic", "gap.line"]},
             {"box": "cav.sel", "dots": [{"who": "A", "path": ["author>cav", "~cav.no"]}],
              "rows": ["gap.model"]}]
    views = [
        {"id": "v", "commit": commit, "reviewed": "2026-10-30", "facts": stated, "elements": []},
        {"id": "g", "commit": commit, "reviewed": "2026-10-30", "example": ["e", "f"],
         "elements": [{"id": "author"}], "wires": [{"id": "author>cav"}],
         "generated": {"example": "graph", "key": "graph"},
         "flows": [{"id": "story", "lanes": {"example": "methods", "key": "lanes"}, "steps": steps},
                   {"id": "inline", "lanes": {"rows": [{"id": "play"}]},
                    "steps": [{"box": "author", "rows": ["play", "gap.line"]}]}]}]
    for view in views:
        (tmp_path / f"docs/how-code-works-view-{view['id']}.js").write_text(view_file(view))
    example = {"f": {"files": {"src/pkg/b.py": digest("old")}},  # e excuses b.py, f does not
               "graph": {"graph": {"elements": [{"id": "cav.own"}], "wires": [{"id": "cav>own"}]}},
               "methods": {"lanes": {"rows": [{"id": "basic", "header": True},
                                              {"id": "gap.line"}]}}}
    (tmp_path / "docs/how-code-works-example-f.js").write_text(
        f"// examples\nObject.assign(DIAGRAM_EXAMPLES, {json.dumps(example)});\n")
    commit_all(tmp_path, "methods")
    assert flags()["v"]["reasons"] == []
    assert flags()["g"] == {"flagged": True, "moved": {},
                            "example_changed": ["src/pkg/a.py", "src/pkg/b.py"], "reasons": [
        "example e: src/pkg/a.py changed since the example was made",
        "example f: src/pkg/b.py changed since the example was made",
        "flow story step 2: its box cav.sel is not in the view",
        "flow story step 2: its wire cav.no is not in the view",
        "flow story step 2: its row gap.model is not in the view",
        "flow inline step 1: its row gap.line is not in the view"]}
    edit(tmp_path, f"{battle}controllers.py", ', "commander": PROMPT', "")
    edit(tmp_path, f"{battle}controllers.py", '"v22"', '"v23"')  # only a value changes
    edit(tmp_path, f"{battle}scripted.py", "}", ', "rush_nearest": Rush}')
    edit(tmp_path, f"{battle}graph_author.py", "}", ', "shoot": "z"}')
    commit_all(tmp_path, "new names and versions")
    assert flags()["v"]["reasons"] == [
        f"{battle}controllers.py MODEL_PROMPTS is now ['llm']; the view says ['commander', 'llm']",
        f"{battle}scripted.py POLICIES is now ['attack_nearest', 'hold', 'rush_nearest']; the view"
        " says ['attack_nearest', 'hold']",
        f"{battle}graph_author.py DESCRIPTIONS is now ['engage', 'owned', 'shoot']; the view says"
        " ['engage', 'owned']",
        f"{battle}controllers.py VERSIONS is now ['commander=v8', 'llm=v23']; the view says"
        " ['commander=v8', 'llm=v22']"]


def test_a_diagram_failure_never_changes_the_exit_code_or_the_pass_record(
        repo, tmp_path_factory, monkeypatch, capsys):
    (repo / "pytest.ini").write_text("[pytest]\n")
    (repo / "ruff.toml").write_text('[lint]\nselect = ["F"]\n')
    (repo / ".gitignore").write_text("runs/\n")

    def broken(*args, **kwargs):
        raise RuntimeError("no such view")

    monkeypatch.setattr(check, "diagram_flags", broken)
    assert run_main(repo, monkeypatch) == 0
    assert "\ndiagram   could not run: no such view" in capsys.readouterr().out
    assert json.loads((repo / check.CHECKED).read_text())["tree"] == check.tree_content(repo)
    assert not (repo / check.DIAGRAM_DATA).exists()
    monkeypatch.undo()
    assert run_main(repo, monkeypatch) == 0  # unbroken: a count and the page's ignored data file
    assert "\ndiagram   0 views flagged, see the log" in capsys.readouterr().out
    assert (repo / check.DIAGRAM_DATA).read_text().startswith("DIAGRAM_FLAGS = {")
    commit_all(repo, "gate files")  # skipped where old commits or the main runs/ are missing
    for kind, args in (("shallow", ["clone", "-q", "--depth", "1", f"file://{repo}"]),
                       ("linked", ["worktree", "add", "-q"])):
        other = tmp_path_factory.mktemp(kind) / "copy"
        git(repo, *args, str(other))
        (other / "docs/state.md").write_text("# Project state\n")
        monkeypatch.setattr(check, "diagram_flags", broken)  # a run must not get this far
        assert run_main(other, monkeypatch) == 0
        assert {"shallow": "\ndiagram   skipped: a shallow clone has no old commits",
                "linked": "\ndiagram   skipped: a linked worktree; run it in the main checkout"
                }[kind] in capsys.readouterr().out
