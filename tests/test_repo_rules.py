"""Repository rules from AGENTS.md that a test can decide.

- `gameai` never imports a game package (Layout).
- No run evidence, game, save or weights file, and no API or private key is tracked, or waits
  untracked to be committed (Experiment and Artifact Rules).
- AGENTS.md stays a short map: at most 200 lines (docs/workflow.md, keeping the process working).
- A WH3 `*_readings.py` module, which reads finished battles for the evaluator, loads no module
  that holds an evaluation battle's witness or controls (owner, 2026-11-15, "F1: readings off
  witnesses"), so editing a witness file cannot change how a battle is read. From
  `twwarhammer3.battle` it imports only three shared helper modules and a battle's `*_facts.py`,
  and those reach only the four modules READINGS_MAY_LOAD adds. Three of the listed modules
  define other controllers (`scripted.py`: hold and the rushes; `skills.py` and `llm.py`, reached
  for one constant), and the rule does not keep readings away from those.

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
# The twwarhammer3.battle modules a readings module may import besides a *_facts module: the
# evidence rules and the helpers witnesses and readings share. READINGS_MAY_LOAD adds what those
# import in turn today (evidence_rules: setup; unit_geometry: skills for OUT, which imports llm,
# which imports benchmark), so that a new path to a witness module fails the test. A *_facts
# module imports nothing from the package.
READINGS_MAY_IMPORT = ("evidence_rules", "scripted", "unit_geometry")
READINGS_MAY_LOAD = (*READINGS_MAY_IMPORT, "setup", "skills", "llm", "benchmark")
READINGS_RULE = "a readings module loads no witness module"
BATTLE = ["twwarhammer3", "battle"]


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


def battle_imports(path: Path) -> list[tuple[int, str]]:
    """(line, module) for each twwarhammer3.battle module a file of that package imports, in
    every import statement's form, relative ones included. The module is "the package" where
    only twwarhammer3 or twwarhammer3.battle is named, since a module is then reached as an
    attribute, and "by a call" for importlib or __import__."""
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Name) and node.id == "__import__":
            found.add((node.lineno, "by a call"))
        if isinstance(node, ast.Import):
            targets = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = BATTLE[:3 - node.level] if node.level else []
            module = ".".join([*base, *([node.module] if node.module else [])])
            targets = [f"{module}.{alias.name}" for alias in node.names]
        else:
            continue
        for parts in (target.split(".") for target in targets):
            if parts[0] == "importlib":
                found.add((node.lineno, "by a call"))
            elif parts in (BATTLE[:1], BATTLE):
                found.add((node.lineno, "the package"))
            elif parts[:2] == BATTLE:
                found.add((node.lineno, parts[2]))
    return sorted(found)


def readings_loads(battle: Path) -> list[str]:
    """What breaks the readings rule in a twwarhammer3.battle directory: each import, in a
    readings module or in a module it reaches, of a module outside the lists above."""
    found = set()
    for start in sorted(battle.glob("*_readings.py")):
        seen, queue = {start.stem}, [start]
        while queue:
            path = queue.pop(0)
            allowed = (READINGS_MAY_IMPORT if path == start else
                       () if path.stem.endswith("_facts") else READINGS_MAY_LOAD)
            for line, name in battle_imports(path):
                if name == "by a call" and path != start and not path.stem.endswith("_facts"):
                    continue  # a shared helper's own importlib use is not followed
                if name not in allowed and not (path == start and name.endswith("_facts")):
                    found.add(f"{path.name}:{line} imports {name}, which {start.name} would "
                              f"load: {READINGS_RULE}")
                elif name not in seen and (battle / f"{name}.py").is_file():
                    seen.add(name)
                    queue.append(battle / f"{name}.py")
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
    assert readings_loads(ROOT / "src" / "twwarhammer3" / "battle") == []


def test_planted_witness_imports_in_and_behind_a_readings_module_are_caught(tmp_path):
    files = {
        "clean_readings.py": (
            '"""Mentions twwarhammer3.battle.camp only in text."""\n'
            "from math import inf\n"
            "from twwarhammer3.battle.camp_facts import CUE_M\n"
            "from twwarhammer3.battle import evidence_rules\n"
            "from .scripted import distance\n"
            "from twwarhammer3.battle.unit_geometry import _centre\n"
            "from twwarhammer3.protocol import visible_enemies\n"),
        "planted_readings.py": (
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
        # Behind an allowed import: a facts module and a shared helper that import a witness.
        "behind_readings.py": ("from twwarhammer3.battle.lines_facts import LINE\n"
                               "from twwarhammer3.battle.unit_geometry import _active\n"),
        "lines_facts.py": "from twwarhammer3.battle.scripted import distance\n",
        "unit_geometry.py": ("from twwarhammer3.battle.skills import OUT\n"
                             "from .calibration import NEIGHBOURS\n"),
        "camp_facts.py": "CUE_M = 30\n", "evidence_rules.py": "", "scripted.py": "",
        "skills.py": "import importlib\n", "calibration.py": "", "setup.py": "",
        "camp.py": "from twwarhammer3.battle.calibration import CornerHold\n"}
    for name, text in files.items():
        (tmp_path / name).write_text(text)
    planted = [(1, "camp"), (2, "lines"), (3, "calibration"), (4, "escalade"),
               (5, "wall_defence"), (6, "camp"), (7, "the package"), (8, "the package"),
               (9, "by a call"), (11, "by a call"), (12, "setup")]
    assert readings_loads(tmp_path) == sorted(
        [f"planted_readings.py:{line} imports {name}, which planted_readings.py would load: "
         f"{READINGS_RULE}" for line, name in planted]
        + [f"lines_facts.py:1 imports scripted, which behind_readings.py would load: "
           f"{READINGS_RULE}",
           f"unit_geometry.py:2 imports calibration, which behind_readings.py would load: "
           f"{READINGS_RULE}",
           f"unit_geometry.py:2 imports calibration, which clean_readings.py would load: "
           f"{READINGS_RULE}"])


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
