"""scripts/refusal_sweep.py on a toy package: each refusal is scored on its own (2026-10-29 bugs:
a `raise ... from` edit that no longer parsed was counted caught; a cached .pyc of the previous
plant ran in a plant's place).
"""
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
'''

TESTS = '''import pytest
import toy


def test_a():
    with pytest.raises(ValueError):
        toy.a(-1)


def test_c():
    with pytest.raises(ValueError):
        toy.c(None)
'''


def test_each_refusal_is_scored_on_its_own_and_the_file_comes_back(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src/toy.py").write_text(TOY)
    (tmp_path / "tests/test_toy.py").write_text(TESTS)
    result = subprocess.run([sys.executable, str(ROOT / "scripts/refusal_sweep.py"), str(tmp_path),
                             "src/toy.py", "x", "x", "tests"], capture_output=True, text=True,
                            timeout=300)
    lines = result.stdout.splitlines()
    assert result.returncode == 0, result.stderr
    assert lines[0].startswith("baseline: exit 0")
    # b's plant has the size of a's and follows its fast failure: it must not inherit it.
    assert [line.split(" ", 2)[:2] for line in lines[1:4]] == [
        ["caught:", "src/toy.py:3"], ["MISSED:", "src/toy.py:9"], ["caught:", "src/toy.py:17"]]
    assert lines[-1] == "2 of 3 removals caught or hung"
    assert (tmp_path / "src/toy.py").read_text() == TOY
    assert not list(tmp_path.rglob("__pycache__"))
