"""Repository rules from AGENTS.md that a test can decide.

- `gameai` never imports a game package (Layout).
- No run evidence, game, save or weights file, and no API or private key is tracked, or waits
  untracked to be committed (Experiment and Artifact Rules).
- AGENTS.md stays short: at most 305 lines until the docs cleanup, then 200 (light factory
  plan, B2).

The first two rules also run on a planted violation, so a rule that can no longer fail shows up
here. JUDGEMENT markers are only listed (scripts/check.py): only the owner changes them.
Followed: transformers' `make check-repository-consistency` (utils/check_repo.py), repository
rules as plain checks beside the tests.
"""

import ast
import re
import subprocess
from fnmatch import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAMES = sorted(p.name for p in (ROOT / "src").iterdir()
               if (p / "__init__.py").is_file() and p.name != "gameai")
# The game, save and weights patterns in .gitignore, and Windows download marks.
FORBIDDEN = ("*.jar", "*.class", "*.exe", "*.dll", "*.sav", "*.pack", "*.autosave*", "*.pt",
             "*.pth", "*.safetensors", "*:Zone.Identifier")
KEY = re.compile(rb"sk-(?:or-v1-|proj-)?[A-Za-z0-9_-]{32,}|-----BEGIN [A-Z ]*PRIVATE KEY-----")
AGENTS_MD_LINES = 305


def game_imports(package: Path) -> list[str]:
    found = []
    for path in sorted(package.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names = [node.module or ""]
            else:
                continue
            found += [f"{path.relative_to(package.parent)}:{node.lineno} imports {name}: "
                      "gameai never imports a game package"
                      for name in names if name.split(".")[0] in GAMES]
    return found


def forbidden_files(root: Path, names: list[str]) -> list[str]:
    found = []
    for name in names:
        if name.startswith("runs/") and name != "runs/README.md":
            found.append(f"{name}: run evidence stays out of Git")
        elif any(fnmatch(name, pattern) for pattern in FORBIDDEN):
            found.append(f"{name}: game, save or weights file")
        elif KEY.search((root / name).read_bytes()):
            found.append(f"{name}: holds what looks like an API or private key")
    return found


def committable() -> list[str]:
    listed = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                            cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return sorted(name for name in listed.split("\0") if name and (ROOT / name).is_file())


def test_gameai_imports_no_game():
    assert GAMES == ["spire", "twwarhammer3"]
    assert game_imports(ROOT / "src" / "gameai") == []


def test_a_planted_game_import_is_caught(tmp_path):
    package = tmp_path / "gameai"
    package.mkdir()
    (package / "clean.py").write_text('"""Mentions twwarhammer3 and spire only in text."""\n'
                                      "import json  # not twwarhammer3\n")
    (package / "planted.py").write_text("def f():\n    from twwarhammer3 import protocol\n"
                                        "    import spire.policies\n")
    assert game_imports(package) == [
        "gameai/planted.py:2 imports twwarhammer3: gameai never imports a game package",
        "gameai/planted.py:3 imports spire.policies: gameai never imports a game package"]


def test_no_run_game_or_key_file_can_be_committed():
    assert forbidden_files(ROOT, committable()) == []


def test_planted_run_game_and_key_files_are_caught(tmp_path):
    (tmp_path / "runs").mkdir()
    files = {"runs/README.md": "ok", "runs/job.log": "x", "mods/BaseMod.jar": "x",
             "docs/note.md": "key sk-" + "a1" * 20 + "\n", "docs/fine.md": "sk-test-secret"}
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
    assert forbidden_files(tmp_path, sorted(files)) == [
        "docs/note.md: holds what looks like an API or private key",
        "mods/BaseMod.jar: game, save or weights file",
        "runs/job.log: run evidence stays out of Git"]


def test_agents_md_stays_short():
    lines = len((ROOT / "AGENTS.md").read_text(encoding="utf-8").splitlines())
    assert lines <= AGENTS_MD_LINES, (
        f"AGENTS.md has {lines} lines, over {AGENTS_MD_LINES}: move detail to the page it governs")
