"""Claude Code and Codex get the same hooks, reviewer agent and skills (owner, 2026-10-29: "I
keep alternating between Codex and Claude Code. In that case, we'll need to keep their
hooks,skills,etc in sync"). Claude Code reads .claude/, Codex .codex/ and .agents/skills/; each
pair below must match. Claude Code's workflows have no Codex counterpart (docs/workflow.md,
"Claude Code and Codex").
"""
import json
import os
import re
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = re.compile(r"scripts/hooks/[\w.]+\.py")


def hooks(path: Path) -> list[tuple]:
    """(event, matcher, script, timeout) for each registered command."""
    config = json.loads(path.read_text(encoding="utf-8"))["hooks"]
    return sorted((event, group.get("matcher", ""), SCRIPT.search(hook["command"]).group(),
                   hook.get("timeout"))
                  for event, groups in config.items() for group in groups
                  for hook in group["hooks"])


def test_both_tools_run_the_same_hook_scripts_on_the_same_events():
    claude = hooks(ROOT / ".claude/settings.json")
    assert claude and claude == hooks(ROOT / ".codex/hooks.json")
    assert all((ROOT / script).is_file() for _, _, script, _ in claude)


def test_each_tools_hook_commands_find_their_scripts_from_a_subfolder():
    # Claude Code sets CLAUDE_PROJECT_DIR; Codex sets no such variable and runs a hook in the
    # session's folder, so its commands must find the repository by themselves.
    plain = {key: value for key, value in os.environ.items() if not key.startswith("CLAUDE")}
    for name, env in ((".claude/settings.json", {**plain, "CLAUDE_PROJECT_DIR": str(ROOT)}),
                      (".codex/hooks.json", plain)):
        config = json.loads((ROOT / name).read_text(encoding="utf-8"))["hooks"]
        for hook in (hook for groups in config.values() for group in groups
                     for hook in group["hooks"]):
            program, _, script = hook["command"].partition(" ")
            shown = subprocess.run(["sh", "-c", f"printf %s {script}"], cwd=ROOT / "docs",
                                   env=env, capture_output=True, text=True).stdout
            assert program == "python3" and Path(shown) == ROOT / SCRIPT.search(script).group()


def test_each_claude_agent_is_a_codex_agent_with_the_same_text():
    claude, codex = {}, {}
    for path in (ROOT / ".claude/agents").glob("*.md"):
        _, front, body = path.read_text(encoding="utf-8").split("---\n", 2)
        meta = dict(line.split(": ", 1) for line in front.strip().splitlines())
        claude[meta["name"]] = (meta["description"], body.strip())
    for path in (ROOT / ".codex/agents").glob("*.toml"):
        agent = tomllib.loads(path.read_text(encoding="utf-8"))
        codex[agent["name"]] = (agent["description"], agent["developer_instructions"].strip())
    assert claude and claude == codex


def test_each_shared_skill_is_linked_for_claude_code():
    shared = {path.name for path in (ROOT / ".agents/skills").iterdir()
              if (path / "SKILL.md").is_file()}
    linked = {path.name: path for path in (ROOT / ".claude/skills").iterdir()}
    assert shared and set(linked) == shared
    assert all(link.is_symlink() and link.resolve() == (ROOT / ".agents/skills" / name).resolve()
               for name, link in linked.items())
