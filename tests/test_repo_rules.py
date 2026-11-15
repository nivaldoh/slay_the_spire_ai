"""Repository rules from AGENTS.md that a test can decide.

- `gameai` never imports a game package (Layout).
- No run evidence, game, save or weights file, and no API or private key is tracked, or waits
  untracked to be committed (Experiment and Artifact Rules).
- AGENTS.md stays a short map: at most 200 lines (docs/workflow.md, keeping the process working).
- A WH3 `*_readings.py` module, which reads finished battles for the evaluator, loads none of
  the modules written as an evaluation battle's witness and controls (`camp.py`, `lines.py`,
  `wall_defence.py`, `escalade.py`) nor `calibration.py` (owner, 2026-11-15, "F1: readings off
  witnesses"), so editing one of those files cannot change how a battle is read. The test keeps
  it so by allowlist: from the game package a readings module imports only `protocol.py`, three
  shared helper modules and a battle's `*_facts.py`, and those reach only the four modules
  READINGS_MAY_LOAD adds. The rule does not keep readings away from every controller: the
  battles also use `scripted.py`'s hold and rushes as controls, and `skills.py` and `llm.py` are
  reached for one constant.

The first two rules and the last also run on a planted violation, so a rule that can no longer
fail shows up here. JUDGEMENT markers are only listed (scripts/check.py): only the owner
changes them.
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
# OpenRouter's hex keys; OpenAI's start a token and mix case and digits, so a slug such as
# "risk-based-..." or "task-..." is not one; PEM private keys.
KEY = re.compile(rb"(?<![\w-])sk-or-v1-[0-9a-f]{64}"
                 rb"|(?<![\w-])sk-(?=[\w-]*[0-9])(?=[\w-]*[A-Z])[\w-]{32,}"
                 rb"|-----BEGIN [A-Z ]*PRIVATE KEY-----")
AGENTS_MD_LINES = 200
# The modules of the game package, named from its root, that a readings module may import besides
# a battle's *_facts module: the protocol, the evidence rules and the helpers witnesses and
# readings share. READINGS_MAY_LOAD adds what those import in turn today (evidence_rules: setup;
# unit_geometry: skills for OUT, which imports llm, which imports benchmark), so that a new import
# statement leading anywhere else in the package fails the test. A *_facts module and the two
# package files import nothing from the package. Not followed: an import made by a call inside a
# helper module, exec and the like, and the tests' own fixtures, which do use the witness modules.
READINGS_MAY_IMPORT = ("protocol", "battle.evidence_rules", "battle.scripted",
                       "battle.unit_geometry")
READINGS_MAY_LOAD = (*READINGS_MAY_IMPORT, "battle.setup", "battle.skills", "battle.llm",
                     "battle.benchmark")
READINGS_RULE = "a readings module loads no witness module"


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


def game_module(root: Path, name: str) -> Path | None:
    """The file of a module of the game package at `root`, named from it ("" is the package)."""
    base = root.joinpath(*filter(None, name.split(".")))
    return next((path for path in (base.with_suffix(".py"), base / "__init__.py")
                 if path.is_file()), None)


def module_imports(root: Path, name: str) -> list[tuple[int, str]]:
    """(line, module) for each module of the game package that module `name` imports, in every
    import statement's form, relative ones included. The module is named from the package root.
    It is "a package" where only the package or a sub-package is named, since a module is then
    reached as an attribute, and "by a call" for importlib or __import__."""
    path = game_module(root, name)
    package = name if path.name == "__init__.py" else name.rpartition(".")[0]
    own = [root.name, *filter(None, package.split("."))]
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Name) and node.id == "__import__":
            found.add((node.lineno, "by a call"))
        if isinstance(node, ast.Import):
            targets = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = own[:len(own) + 1 - node.level] if node.level else []
            module = ".".join([*base, *([node.module] if node.module else [])])
            targets = [f"{module}.{alias.name}" for alias in node.names]
        else:
            continue
        for parts in (target.split(".") for target in targets):
            if parts[0] == "importlib":
                found.add((node.lineno, "by a call"))
            elif parts[0] == root.name:
                parts = parts[1:]  # then the longest prefix that is a module's file
                while parts and game_module(root, ".".join(parts)) is None:
                    parts.pop()
                file = game_module(root, ".".join(parts))
                found.add((node.lineno, "a package" if file is None
                           or file.name == "__init__.py" else ".".join(parts)))
    return sorted(found)


def readings_loads(root: Path) -> list[str]:
    """What breaks the readings rule in the game package at `root`: each import, in a readings
    module, in a module it reaches or in a package file that runs before it, of a module outside
    the lists above."""
    found = set()
    for start in sorted((root / "battle").glob("*_readings.py")):
        first = f"battle.{start.stem}"
        seen = {first, "", "battle"}
        queue = [name for name in (first, "", "battle") if game_module(root, name)]
        while queue:
            name = queue.pop(0)
            allowed = (READINGS_MAY_IMPORT if name == first else
                       () if name.endswith("_facts") or name in ("", "battle") else
                       READINGS_MAY_LOAD)
            for line, target in module_imports(root, name):
                if target == "by a call" and allowed is READINGS_MAY_LOAD:
                    continue  # a shared helper's own importlib use is not followed
                if target not in allowed and not (name == first and target.endswith("_facts")):
                    found.add(f"{game_module(root, name).relative_to(root)}:{line} imports "
                              f"{target}, which {start.name} would load: {READINGS_RULE}")
                elif target not in seen:
                    seen.add(target)
                    queue.append(target)
    return sorted(found)


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


def test_wh3_readings_load_no_witness_module():
    assert readings_loads(ROOT / "src" / "twwarhammer3") == []


def test_planted_witness_imports_in_and_behind_a_readings_module_are_caught(tmp_path):
    root = tmp_path / "twwarhammer3"
    files = {
        "__init__.py": "",
        # A package file runs before every readings module.
        "battle/__init__.py": "from twwarhammer3.battle import wall_defence\n",
        "protocol.py": "def late():\n    from twwarhammer3.battle.camp import GUNS\n",
        "battle/clean_readings.py": (
            '"""Mentions twwarhammer3.battle.camp only in text."""\n'
            "from math import inf\n"
            "from twwarhammer3.battle.camp_facts import CUE_M\n"
            "from twwarhammer3.battle import evidence_rules\n"
            "from .scripted import distance\n"
            "from twwarhammer3.battle.unit_geometry import _centre\n"
            "from twwarhammer3.protocol import visible_enemies\n"),
        "battle/planted_readings.py": (
            "from twwarhammer3.battle.camp import CUE_M\n"
            "from twwarhammer3.battle import lines\n"
            "import twwarhammer3.battle.calibration\n"
            "from .escalade import front_line\n"
            "from . import wall_defence\n"
            "from ..battle.camp import GUNS\n"
            "import twwarhammer3.battle\n"
            "from twwarhammer3 import battle\n"
            "import importlib\n"
            "def late():\n"
            "    return __import__('twwarhammer3.battle.camp')\n"
            "from twwarhammer3.battle.setup import scenarios\n"),
        # Behind allowed imports: a facts module, and a witness three imports away.
        "battle/behind_readings.py": ("from twwarhammer3.battle.lines_facts import LINE\n"
                                      "from twwarhammer3.battle.unit_geometry import _active\n"),
        "battle/lines_facts.py": ("import importlib\n"
                                  "from twwarhammer3.battle.scripted import distance\n"),
        "battle/unit_geometry.py": "from twwarhammer3.battle.skills import OUT\n",
        "battle/skills.py": "import importlib\nfrom .llm import LLMPolicy\n",  # a helper may
        "battle/llm.py": "from twwarhammer3.battle.escalade import front_line\n",
        "battle/evidence_rules.py": "import twwarhammer3.battle\n",
        "battle/camp_facts.py": "CUE_M = 30\n", "battle/scripted.py": "", "battle/setup.py": "",
        "battle/camp.py": "from twwarhammer3.battle.calibration import CornerHold\n",
        "battle/lines.py": "", "battle/calibration.py": "", "battle/escalade.py": "",
        "battle/wall_defence.py": ""}
    for name, text in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text)
    package = ("battle/__init__.py", 1, "battle.wall_defence")
    behind = ("battle/llm.py", 1, "battle.escalade")
    planted = {
        "planted_readings.py": [package] + [("battle/planted_readings.py", line, name) for
                                            line, name in (
            (1, "battle.camp"), (2, "battle.lines"), (3, "battle.calibration"),
            (4, "battle.escalade"), (5, "battle.wall_defence"), (6, "battle.camp"),
            (7, "a package"), (8, "a package"), (9, "by a call"), (11, "by a call"),
            (12, "battle.setup"))],
        "clean_readings.py": [package, behind, ("protocol.py", 2, "battle.camp"),
                              ("battle/evidence_rules.py", 1, "a package")],
        "behind_readings.py": [package, behind, ("battle/lines_facts.py", 1, "by a call"),
                               ("battle/lines_facts.py", 2, "battle.scripted")]}
    assert readings_loads(root) == sorted(
        f"{file}:{line} imports {name}, which {start} would load: {READINGS_RULE}"
        for start, items in planted.items() for file, line, name in items)


def test_no_run_game_or_key_file_can_be_committed():
    assert forbidden_files(ROOT, committable()) == []


def test_planted_run_game_and_key_files_are_caught(tmp_path):
    (tmp_path / "runs").mkdir()
    files = {"runs/README.md": "ok", "runs/job.log": "x", "mods/BaseMod.jar": "x",
             "docs/note.md": "key sk-" + "Ab1" * 14 + "\n", "docs/or.md": "sk-or-v1-" + "0f" * 32,
             "docs/fine.md": "sk-test-secret, #risk-based-checks-for-long-autonomous-runs-2"}
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
    assert forbidden_files(tmp_path, sorted(files)) == [
        "docs/note.md: holds what looks like an API or private key",
        "docs/or.md: holds what looks like an API or private key",
        "mods/BaseMod.jar: game, save or weights file",
        "runs/job.log: run evidence stays out of Git"]


def test_agents_md_stays_short():
    lines = len((ROOT / "AGENTS.md").read_text(encoding="utf-8").splitlines())
    assert lines <= AGENTS_MD_LINES, (
        f"AGENTS.md has {lines} lines, over {AGENTS_MD_LINES}: move detail to the page it governs")
