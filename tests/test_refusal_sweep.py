"""scripts/refusal_sweep.py on a toy package: each refusal is scored on its own (2026-10-29 bugs:
a `raise ... from` edit that no longer parsed was counted caught; a cached .pyc of the previous
plant ran in a plant's place).
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TOY = '''def a(x):
    if x < 0:
        raise ValueError("neg a")
    return x


def b(x):
    if x < 0:
        raise ValueError("neg b")
    return x


def c(x):
    try:
        return int(x)
    except TypeError as error:
        raise ValueError("bad c") from error


def d(rank):
    # A multi-byte character before the end column: ast counts bytes, the file characters.
    if not 0 <= rank <= 9:
        raise ValueError("ranks 0–9 only")
    return rank


def e(x):
    if x < 0:
        raise ValueError("neg e")
    while x < 0:
        pass
    return x
'''

TESTS = '''import pytest
import toy


def test_a():
    with pytest.raises(ValueError):
        toy.a(-1)


def test_c():
    with pytest.raises(ValueError):
        toy.c(None)


def test_d():
    with pytest.raises(ValueError):
        toy.d(10)


def test_e():
    with pytest.raises(ValueError):
        toy.e(-1)
'''


def sweep(tmp_path, tests=TESTS):
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "tests").mkdir(exist_ok=True)
    (tmp_path / "src/toy.py").write_text(TOY)
    (tmp_path / "tests/test_toy.py").write_text(tests)
    return subprocess.run([sys.executable, str(ROOT / "scripts/refusal_sweep.py"), str(tmp_path),
                           "src/toy.py", "x", "x", "tests"], capture_output=True, text=True,
                          timeout=300, env={**os.environ, "SWEEP_TIMEOUT": "3"})


def test_each_refusal_is_scored_on_its_own_and_the_file_comes_back(tmp_path):
    result = sweep(tmp_path)
    lines = result.stdout.splitlines()
    assert result.returncode == 0, result.stderr
    assert lines[0].startswith("baseline: exit 0")
    # b's plant has the size of a's and follows its fast failure: it must not inherit it.
    assert [line.split(" ", 2)[:2] for line in lines[1:6]] == [
        ["caught:", "src/toy.py:3"], ["MISSED:", "src/toy.py:9"], ["caught:", "src/toy.py:17"],
        ["caught:", "src/toy.py:23"], ["HANG:", "src/toy.py:29"]]  # a hang counts as caught
    assert lines[-1] == "4 of 5 removals caught or hung"
    assert (tmp_path / "src/toy.py").read_text() == TOY
    assert not list(tmp_path.rglob("__pycache__"))


def test_a_failing_baseline_or_this_tree_is_refused(tmp_path):
    result = sweep(tmp_path, TESTS + "\n\ndef test_broken():\n    assert False\n")
    assert result.returncode and "baseline fails" in result.stderr
    assert result.stdout.startswith("baseline: exit 1") and "caught" not in result.stdout
    # A copy of the script inside the scratch tree: without its guard it could only touch the toy.
    (tmp_path / "scripts").mkdir()
    script = (ROOT / "scripts/refusal_sweep.py").read_text()
    (tmp_path / "scripts/refusal_sweep.py").write_text(script)
    (tmp_path / "tests/test_toy.py").write_text(TESTS)
    result = subprocess.run([sys.executable, str(tmp_path / "scripts/refusal_sweep.py"),
                             str(tmp_path), "src/toy.py", "x", "x", "tests"], capture_output=True,
                            text=True, timeout=300, env={**os.environ, "SWEEP_TIMEOUT": "3"})
    assert result.returncode and "never this tree" in result.stderr
    assert (tmp_path / "src/toy.py").read_text() == TOY
