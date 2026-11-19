"""Historical source identities and the private-text filter for the public code examples."""

import hashlib
import importlib.util
import subprocess
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "diagram_examples", Path(__file__).resolve().parents[1] / "scripts" / "diagram_examples.py")
examples = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(examples)


@pytest.mark.parametrize("text", [
    r"C:\Users\someone", r"C:\\Users\\someone", r"C:\\\\Users\\\\someone", r"D:\Users\someone",
    "C:/Users/someone", "/home/someone", r"\\wsl$\home\someone", r"\\DESKTOP-ABC\c$\Users\someone",
    "/mnt/c/Users/someone", "/mnt/d/Users/someone", "someone@example.com",
    "first.last@mail.example.org", "first+tag@example.com", "SOMEONE@EXAMPLE.COM",
    "_someone@example.com_", "someone@example.com_backup", "someone@example.com2", "a@b.c",
    "a@host.domain1", "a@пример.рф", "niv@10.0.0.4", "ssh niv@34.123.45.67:22",
    "x@host-1.2.example.com", "76561198000000000", "sk-" + "a" * 16, "wrkspc_x"])
def test_private_text_is_refused(text):
    assert examples.PRIVATE.search(text)


@pytest.mark.parametrize("text", [
    "llm@gpt-5.4/low", "commander@claude-opus-4.7", '"commander@claude-opus-4.7"', "llm@glm-5/low",
    "llm_rules@z-ai/glm-5.3/low", "runs/twwarhammer3/battle"])
def test_a_model_label_or_repository_path_is_not_private(text):
    assert not examples.PRIVATE.search(text)


def test_a_moved_source_keeps_its_battle_name_hash_and_constant(tmp_path, monkeypatch):
    def git(*args):
        return subprocess.check_output(["git", "-c", "user.name=Test", "-c",
                                        "user.email=test@invalid.test", *args],
                                       cwd=tmp_path, text=True).strip()

    git("init", "-q")
    old, current = "src/old.py", "src/current.py"
    code = b"TIMEOUT_MS = 4000\n"
    (tmp_path / "src").mkdir()
    (tmp_path / old).write_bytes(code)
    git("add", old)
    git("commit", "-qm", "Record the battle code")
    battle = git("rev-parse", "HEAD")
    git("mv", old, current)
    git("commit", "-qm", "Move the source file")
    monkeypatch.setattr(examples, "ROOT", tmp_path)
    assert examples.cited_files("", battle, [current]) == ({old: hashlib.sha256(code).hexdigest()},
                                                           [old])
    assert examples.head_constant(current, "TIMEOUT_MS", battle) == 4000
