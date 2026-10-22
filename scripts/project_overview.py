"""Build the local project overview from docs/state.md, without games or API calls.

    uv run --locked python scripts/project_overview.py

Open runs/project-overview/index.html. Rebuild after changing docs/state.md; the page
is a snapshot, not a live process monitor. Only paragraphs, lists, links, inline code
and bold text are needed by the state page; this is not a general Markdown renderer.
"""

import argparse
import hashlib
import html
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "docs/state.md"
TEMPLATE = Path(__file__).with_name("project_overview.html")
TRACKS = ("Total War: WARHAMMER III", "Slay the Spire", "Post-training")
CONTEXT = ("Known issues", "Branches", "Runtime and ownership")
REQUIRED = ("Active work", *TRACKS, "Owner decisions waiting", *CONTEXT)
TOKEN = re.compile(r"`([^`]+)`|\[([^\]]+)\]\(([^)]+)\)|\*\*(.+?)\*\*")


def slug(title: str) -> str:
    title = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", title)
    parts = re.split(r"(`+[^`]*`+)", title)
    title = "".join(part.strip("`") if part.startswith("`") else re.sub(r"<[^>]+>", "", part)
                    for part in parts)
    return re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")


def sections(document: str) -> dict[str, str]:
    parts = re.split(r"^## (.+)\n", document, flags=re.M)
    result = dict(zip(parts[1::2], (part.strip() for part in parts[2::2]), strict=True))
    missing = set(REQUIRED) - result.keys()
    if missing:
        raise ValueError(f"state.md is missing sections: {', '.join(sorted(missing))}")
    return result


def link(target: str, source: Path, output: Path) -> str | None:
    parsed = urlsplit(target)
    if parsed.scheme:
        return target if parsed.scheme in {"https", "http", "mailto"} else None
    path = (source.parent / unquote(parsed.path)).resolve() if parsed.path else source
    if path == source and parsed.fragment:
        return "#" + parsed.fragment
    if path.suffix == ".md" and path.is_relative_to(ROOT):
        relative = "sources/" + path.relative_to(ROOT).with_suffix(".html").as_posix()
    else:
        relative = Path(os.path.relpath(path, output.parent)).as_posix()
    return quote(relative) + ("#" + parsed.fragment if parsed.fragment else "")


def inline(text: str, source: Path, output: Path) -> str:
    result, end = [], 0
    for match in TOKEN.finditer(text):
        result.append(html.escape(text[end:match.start()]))
        code, label, target, bold = match.groups()
        if code is not None:
            result.append(f"<code>{html.escape(code)}</code>")
        elif label is not None:
            href = link(target, source, output)
            label = html.escape(label)
            result.append(f'<a href="{html.escape(href, quote=True)}">{label}</a>'
                          if href else label)
        else:
            result.append(f"<strong>{html.escape(bold)}</strong>")
        end = match.end()
    result.append(html.escape(text[end:]))
    return "".join(result)


def markdown(text: str, source: Path, output: Path) -> str:
    result = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.splitlines()
        if not lines:
            continue
        if re.match(r"^(?:- |\d+\. )", lines[0]):
            ordered = not lines[0].startswith("- ")
            tag = "ol" if ordered else "ul"
            items = re.split(r"^(?:- |\d+\. )", block, flags=re.M)[1:]
            start = f' start="{int(lines[0].split(".", 1)[0])}"' if ordered else ""
            result.append(f"<{tag}{start}>" + "".join(
                "<li>" + inline(" ".join(item.split()), source, output) + "</li>"
                for item in items) + f"</{tag}>")
        else:
            result.append("<p>" + inline(" ".join(block.split()), source, output) + "</p>")
    return "\n".join(result)


def summary_and_detail(text: str) -> tuple[str, str]:
    first, _, rest = text.partition("\n\n")
    return first, rest


def render(document: str, source: Path, output: Path, generated: datetime) -> str:
    data = sections(document)
    updated = re.search(r"^Updated (\d{4}-\d{2}-\d{2}):", document, flags=re.M)
    if not updated:
        raise ValueError("state.md needs an 'Updated YYYY-MM-DD:' date")
    inbox = data["Owner decisions waiting"]
    parts = re.split(r"^(\d+)\. ", inbox, flags=re.M)
    decisions = parts[2::2]
    numbers = [int(number) for number in parts[1::2]]
    if inbox != "None." and (not decisions or parts[0].strip()
                            or numbers != list(range(1, len(numbers) + 1))):
        raise ValueError("Owner decisions waiting needs numbered topics, or 'None.'")

    def body(text: str) -> str:
        return markdown(text, source, output)

    active, active_detail = summary_and_detail(data["Active work"])
    tracks = []
    for index, title in enumerate(TRACKS, 1):
        first, rest = summary_and_detail(data[title])
        details = (f'<details><summary>Context and next steps</summary>{body(rest)}</details>'
                   if rest else "")
        tracks.append(f'<article class="track" id="{slug(title)}">'
                      f'<span class="eyebrow">Track 0{index}</span>'
                      f'<h3>{html.escape(title)}</h3>{body(first)}{details}</article>')
    topics = []
    for index, text in enumerate(decisions, 1):
        first, rest = summary_and_detail(text.strip())
        heading = re.match(r"\*\*(.+?)\*\*\s*(.*)", " ".join(first.split()))
        if not heading:
            raise ValueError(f"Decision topic {index} needs a bold title")
        title, question = heading.groups()
        topics.append(
            f'<details class="decision"{" open" if index <= 3 else ""}>'
            f'<summary><span class="number">{index:02}</span>'
            f'<span>{html.escape(title.rstrip("."))}</span></summary>'
            f'<div class="decision-body">{body(question)}{body(rest)}</div></details>')
    context = "\n".join(
        f'<details id="{slug(title)}"><summary>{html.escape(title)}</summary>'
        f'{body(data[title])}</details>' for title in CONTEXT)
    values = {
        "updated": updated[1], "generated": generated.strftime("%Y-%m-%d %H:%M UTC"),
        "fingerprint": hashlib.sha256(document.encode()).hexdigest()[:12],
        "active": body(active), "active_detail": body(active_detail),
        "tracks": "\n".join(tracks), "count": str(len(topics)),
        "decisions": "\n".join(topics) if topics else "<p>No decisions recorded.</p>",
        "context": context,
        "source": link(source.name, source, output),
    }
    # One substitution pass: source prose containing a placeholder stays literal.
    return re.sub(r"\{\{(\w+)\}\}", lambda match: values[match[1]],
                  TEMPLATE.read_text(encoding="utf-8"))


def source_pages(document: str, output: Path) -> None:
    """Keep background documents readable offline, with their heading links intact."""
    paths = {STATE}
    for match in TOKEN.finditer(document):
        target = match[3]
        if target and not urlsplit(target).scheme:
            path = (STATE.parent / unquote(urlsplit(target).path)).resolve()
            if path.suffix == ".md" and path.is_relative_to(ROOT):
                paths.add(path)
    for path in paths:
        seen, lines, fence = {}, [], None
        for line in path.read_text(encoding="utf-8").splitlines():
            marker = re.match(r"^\s*(```|~~~)", line)
            if marker and (fence is None or marker[1] == fence):
                fence = None if fence else marker[1]
            heading = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line) if not fence else None
            if heading:
                base = slug(heading[1])
                count = seen.get(base, 0)
                seen[base] = count + 1
                anchor = base if count == 0 else f"{base}-{count}"
                lines.append(f'<span id="{html.escape(anchor)}"></span>')
            lines.append(html.escape(line))
        destination = output.parent / "sources" / path.relative_to(ROOT).with_suffix(".html")
        destination.parent.mkdir(parents=True, exist_ok=True)
        back = quote(Path(os.path.relpath(output, destination.parent)).as_posix())
        title = html.escape(path.relative_to(ROOT).as_posix())
        destination.write_text(
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{title}</title><style>body{{max-width:90ch;margin:2rem auto;padding:0 1rem;'
            'background:#f4f3ed;color:#203630;font:16px/1.7 system-ui}}'
            'pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.8 ui-monospace,monospace}'
            'a{color:#37664e}span[id]{scroll-margin-top:2rem}</style>'
            f'<a href="{back}">← Project overview</a><h1>{title}</h1>'
            '<p>Source document copied when the overview was built. Markdown shown as written.</p>'
            '<pre>' + "\n".join(lines) + '</pre></html>', encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=ROOT / "runs/project-overview/index.html")
    args = parser.parse_args()
    output = args.output.resolve()
    document = STATE.read_text(encoding="utf-8")
    page = render(document, STATE, output, datetime.now(UTC))
    output.parent.mkdir(parents=True, exist_ok=True)
    source_pages(document, output)
    output.write_text(page, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
