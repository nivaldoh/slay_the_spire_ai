"""Every relative link and #anchor in the repository's Markdown files resolves.

Anchors follow GitHub's heading slugs: lowercase, punctuation other than hyphens and
underscores dropped, each space a hyphen, repeated headings suffixed -1, -2, ...
Links inside code spans and fenced blocks, and http(s) and mailto links, are not checked.
"""

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

import pytest

ROOT = Path(__file__).resolve().parents[1]
FENCE = re.compile(r"^\s*(```|~~~)")
CODE_SPAN = re.compile(r"(`+)(?:(?!\1).)+?\1")
LINK = re.compile(r"!?\[(?:[^\[\]]|\[[^\]]*\])*\]\(\s*<?([^)\s>]*)>?(?:\s+\"[^\"]*\")?\s*\)")
REFERENCE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*<?(\S+?)>?(?:\s|$)", re.M)
HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$")
HTML_ANCHOR = re.compile(r"<a\s+(?:name|id)=\"([^\"]+)\"")


def markdown_files() -> list[Path]:
    try:
        listed = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.md"],
            cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        return []
    return sorted(ROOT / name for name in set(listed) if (ROOT / name).is_file())


def prose(text: str, spans: bool = False) -> list[str]:
    """The lines outside fenced code blocks; inline code spans removed unless spans."""
    lines, fenced = [], None
    for line in text.splitlines():
        fence = FENCE.match(line)
        if fence and (fenced is None or fence.group(1) == fenced):
            fenced = None if fenced else fence.group(1)
            continue
        if fenced is None:
            lines.append(line if spans else CODE_SPAN.sub("", line))
    return lines


def slug(heading: str) -> str:
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", heading)
    parts = re.split(r"(`+[^`]*`+)", text)  # HTML tags are dropped outside code spans only
    text = "".join(p.strip("`") if p.startswith("`") else re.sub(r"<[^>]+>", "", p) for p in parts)
    return re.sub(r"[^\w\- ]", "", text.strip().lower()).replace(" ", "-")


def anchors(path: Path) -> set[str]:
    found, seen = set(), {}
    text = path.read_text(encoding="utf-8")
    for line in prose(text, spans=True):
        heading = HEADING.match(line)
        if heading:
            base = slug(heading.group(1))
            count = seen.get(base, 0)
            seen[base] = count + 1
            found.add(base if count == 0 else f"{base}-{count}")
    found.update(HTML_ANCHOR.findall(text))
    return found


def broken_links(path: Path) -> list[str]:
    broken = []
    text = "\n".join(prose(path.read_text(encoding="utf-8")))  # link text may wrap
    targets = [m.group(1) for m in LINK.finditer(text)]
    targets += [m.group(1) for m in REFERENCE.finditer(text)]
    for target in targets:
        if not target or re.match(r"[a-z][a-z0-9+.-]*:", target, re.I):
            continue  # http(s), mailto and other schemes
        file_part, _, anchor = target.partition("#")
        file_part = unquote(file_part)
        if file_part.startswith("/"):
            resolved = ROOT / file_part.lstrip("/")
        else:
            resolved = (path.parent / file_part).resolve() if file_part else path
        if not resolved.exists():
            broken.append(f"{target}: no such file")
        elif anchor and resolved.suffix == ".md" and unquote(anchor) not in anchors(resolved):
            broken.append(f"{target}: no such anchor")
    return broken


@pytest.mark.parametrize("path", markdown_files(), ids=lambda p: str(p.relative_to(ROOT)))
def test_links_resolve(path):
    assert broken_links(path) == []


def test_slugs_follow_github():
    assert slug("Benchmark harness b9 (2026-10-14, timer classification)") == (
        "benchmark-harness-b9-2026-10-14-timer-classification")
    assert slug("`llm_rules` and the [log](log.md): v1.2 – done") == (
        "llm_rules-and-the-log-v12--done")
    assert slug("Jobs in `runs/<job>` <em>now</em>") == "jobs-in-runsjob-now"


def test_wrapped_links_are_checked(tmp_path):
    page = tmp_path / "page.md"
    page.write_text("# Top\n\nSee the [visual report\nplan](missing.md#nope), [top](#top),\n"
                    "[a bad\nanchor](#gone) and [one line](also-missing.md).\n")
    assert broken_links(page) == ["missing.md#nope: no such file", "#gone: no such anchor",
                                  "also-missing.md: no such file"]
