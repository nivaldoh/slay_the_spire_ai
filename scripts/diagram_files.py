"""Write docs/how-code-works-files.js: every path in the file lists, what it does, and its map box.

The list is the WH3 README's Code map, one file per line (`` - `path`: what it does ``), less
the paths the Map view leaves out (its "outside": Slay the Spire's); the map boxes are the
`files` prefixes of the Map view, docs/how-code-works-view-map.js. The page shows a box's files
when it is clicked. diagram_flags, below, flags paths missing from the list or in no box for
scripts/check.py, so the page and the gate read the list with the same code.

    uv run --locked python scripts/diagram_files.py [--out docs/how-code-works-files.js]

The output, a classic script the page loads, depends only on those two files, so two runs on
one tree write identical files.
"""
import argparse
import ast
import hashlib
import json
import re
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIAGRAM_VIEW = "docs/how-code-works-view-"  # one hand-written view per file: <id>.js
DIAGRAM_EXAMPLE = "docs/how-code-works-example-"  # written by scripts/diagram_examples.py
DIAGRAM_LISTS = {"docs/twwarhammer3/README.md": "## Code map"}  # the page draws WH3 only
DIAGRAM_ENTRY = re.compile(r"^- `([^`\s]+)`: (.+(?:\n  \S.*)*)", re.M)  # one file per line
DIAGRAM_REF = re.compile(r"^([^\s:]+)(?::(\d+)(?:-(\d+))?)?$")
# JUDGEMENT?: Review age — Claude Code, 2026-11-01, plan default 4 ("for example, three
# months", Software Engineering at Google ch. 10): 92 days. A shorter floor flags quiet views
# sooner and costs more refreshes; the "not reviewed" flags rest on it.
DIAGRAM_REVIEW_DAYS = 92


def file_list(text: str, heading: str) -> list[tuple[str, str]]:
    """The (path, description) lines of one list: its heading's section only."""
    start = re.search(rf"^{re.escape(heading)}\n", text, re.M)
    if not start:
        return []
    end = text.find("\n## ", start.end())
    return DIAGRAM_ENTRY.findall(text[start.end():end if end > 0 else len(text)])


def diagram_flags(root: Path, rev: str = "HEAD", views: list | None = None,
                  today: str | None = None) -> dict:
    """Flag the page's views from Git objects at `rev`, by the rules in scripts/check.py's
    docstring ("diagram"). `views` replaces the committed ones (the three-week replay
    re-anchors them); `today` is an ISO date."""

    cat = subprocess.Popen(["git", "cat-file", "--batch"], cwd=root, stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE)
    blobs: dict[str, bytes | None] = {}

    def show(commit: str, path: str) -> bytes | None:
        key = f"{commit}:{path}"
        if key not in blobs:
            cat.stdin.write(key.encode() + b"\n")
            cat.stdin.flush()
            header = cat.stdout.readline().split()
            if header[-1] in (b"missing", b"ambiguous"):
                blobs[key] = None
            else:
                blobs[key] = cat.stdout.read(int(header[2]))
                cat.stdout.read(1)
        return blobs[key]

    def text(commit: str, path: str) -> str | None:
        data = show(commit, path)
        return None if data is None else data.decode("utf-8", "replace")

    def literal(path: str, name: str, values: bool = False) -> list | None:
        # A constant's keys or items, by ast; with `values`, a dict's "key=value" items.
        for node in ast.parse(text(rev, path) or "").body:
            targets = node.targets if isinstance(node, ast.Assign) else (
                [node.target] if isinstance(node, ast.AnnAssign) else [])
            if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                value = node.value
                if isinstance(value, ast.Call) and value.args:  # frozenset({...}), tuple([...])
                    value = value.args[0]
                if isinstance(value, ast.Dict) and values:
                    return sorted(f"{key}={item}" for key, item in ast.literal_eval(value).items())
                if isinstance(value, ast.Dict):
                    return sorted(ast.literal_eval(key) for key in value.keys)
                return sorted(ast.literal_eval(value))
        return None

    try:
        names = git(root, "ls-tree", "-r", "--name-only", rev).splitlines()
        present = set(names)
        if views is None:
            views = [payload(text(rev, name)) for name in names
                     if name.startswith(DIAGRAM_VIEW) and name.endswith(".js")]
        examples: dict = {}
        for name in names:
            if name.startswith(DIAGRAM_EXAMPLE) and name.endswith(".js"):
                examples.update(payload(text(rev, name)))
        day = date.fromisoformat(today) if today else date.today()
        battle = "src/twwarhammer3/battle/"
        # fact: (file, constant, values), values: a dict compared key by key and value by value
        facts = {"providers": ("src/gameai/providers.py", "PROVIDERS", False),
                 "hidden_keys": ("src/twwarhammer3/protocol.py", "HIDDEN_KEYS", False),
                 "model_policies": (f"{battle}controllers.py", "MODEL_PROMPTS", False),
                 "scripted_policies": (f"{battle}scripted.py", "POLICIES", False),
                 "graph_ops": (f"{battle}graph_author.py", "DESCRIPTIONS", False),
                 # JUDGEMENT?: Whole versions — Claude Code, 2026-11-01, final-spec
                 # viewer_changes: a view states VERSIONS whole, so any controller's new version
                 # flags it, drawn or not. Comparing only the stated names would flag less; the
                 # methods card's "on main" versions rest on it.
                 "versions": (f"{battle}controllers.py", "VERSIONS", True)}
        result: dict = {"revision": rev, "date": day.isoformat(), "views": {}}
        for view in views:
            reasons: list[str] = []
            moved: dict[str, str] = {}
            if (day - date.fromisoformat(view["reviewed"])).days > DIAGRAM_REVIEW_DAYS:
                reasons.append(f"not reviewed since {view['reviewed']}, over three months")
            for fact, (path, name, values) in facts.items():
                stated = view.get("facts", {}).get(fact)
                if stated is None:
                    continue
                if values:  # stated as a dict too
                    stated = [f"{key}={item}" for key, item in stated.items()]
                try:
                    found = literal(path, name, values)
                except (SyntaxError, ValueError) as exc:
                    reasons.append(f"cannot read {name} from {path}: {exc}")
                    continue
                if sorted(stated) != found:
                    reasons.append(f"{path} {name} is now {found}; the view says {sorted(stated)}")
            # Cited: the refs of the view, its boxes, wires, notes, cards and flow steps, those of
            # each one's status ({text, refs}) and those of the boxes and wires an example
            # generated for it (view.generated), each read at its item's commit, else the view's.
            generated = view.get("generated") or {}
            made = examples.get(generated.get("example"), {}).get(generated.get("key")) or {}
            items = [view, *view.get("elements", []), *view.get("wires", []),
                     *view.get("notes", []), *view.get("cards", {}).values(),
                     *made.get("elements", []), *made.get("wires", []), made,
                     *(step for flow in view.get("flows", []) for step in flow["steps"])]
            cited = sorted({(item.get("commit") or view["commit"], ref)
                            for item in items
                            for ref in [*(item.get("refs") or []),
                                        *(item["status"].get("refs") or []
                                          if isinstance(item.get("status"), dict) else [])]
                            if not ref.startswith("runs/")})
            for commit, ref in cited:
                match = DIAGRAM_REF.match(ref)
                path = match[1] if match else ref.split()[0]
                if path not in present and not any(n.startswith(path.rstrip("/") + "/")
                                                   for n in names):
                    reasons.append(f"{path} is gone (cited at {commit})")
                    continue
                if not match or not match[2]:
                    continue  # a whole file: only its existence is checked
                first, last = int(match[2]), int(match[3] or match[2])
                old = [line.strip() for line in (text(commit, path) or "").splitlines()
                       [first - 1:last]]
                new = [line.strip() for line in (text(rev, path) or "").splitlines()]
                if not old:
                    reasons.append(f"cannot read {ref} at {commit}")
                    continue
                if new[first - 1:last] == old:
                    continue
                hits = [i for i in range(len(new) - len(old) + 1)
                        if new[i:i + len(old)] == old]
                if hits and any(old):
                    end = f"-{hits[0] + len(old)}" if last > first else ""
                    moved[ref] = f"{path}:{hits[0] + 1}{end}"
                else:
                    reasons.append(f"{ref} changed since {commit}")
            # JUDGEMENT?: Example flags — Claude Code, 2026-11-01, plan section 3 and default 3:
            # a story is flagged only for cited files changed after its example was made;
            # changed_since keeps the "code changed since" badge. Flagging every change since
            # the battle would keep the story flagged until a new battle runs.
            changed: set[str] = set()
            named = view.get("example")  # an id, a list of ids or {made_up: true}
            named = [named] if isinstance(named, str) else named if isinstance(named, list) else []
            example = [(name, examples[name]) for name in named if name in examples]
            if example:
                for name, one in example:
                    mine = set()
                    for path, digest in one["files"].items():
                        data = show(rev, path)
                        if data is None or hashlib.sha256(data).hexdigest() != digest:
                            mine.add(path)
                    changed |= mine
                    for path in sorted(mine - set(one.get("changed_since", []))):
                        reasons.append(f"example {name}: {path} changed since the example"
                                       " was made")
            # A step must name ids the view has: its own boxes and wires, those an example
            # generated (view.generated) and its flow's lane rows, inline or an example's.
            have = {"box": {item.get("id") for item in [*view.get("elements", []),
                                                         *made.get("elements", [])]},
                    "wire": {item.get("id") for item in [*view.get("wires", []),
                                                          *made.get("wires", [])]}}
            for flow in view.get("flows", []):
                lanes = flow.get("lanes") or {}
                if "example" in lanes:  # {example, key}
                    lanes = examples.get(lanes["example"], {}).get(lanes["key"]) or {}
                have["row"] = {row.get("id") for row in lanes.get("rows", [])}
                for number, step in enumerate(flow["steps"], 1):
                    ids = [("box", step["box"])] if step.get("box") else []
                    ids += [("wire", wire.lstrip("~")) for dot in step.get("dots", [])
                            for wire in (dot if isinstance(dot, list) else dot.get("path", []))]
                    ids += [("row", row) for row in step.get("rows", [])]
                    for kind, name in dict.fromkeys(ids):
                        if name not in have[kind]:
                            reasons.append(f"flow {flow.get('id')} step {number}: its {kind}"
                                           f" {name} is not in the view")
            if view["id"] == "map":
                listed = {}
                for page, heading in DIAGRAM_LISTS.items():
                    listed.update(file_list(text(rev, page) or "", heading))
                owners = [prefix for box in view["elements"] for prefix in box.get("files", [])]
                outside = tuple(view.get("outside", []))  # paths the page leaves out
                missing = [n for n in names if n.startswith("src/") and n.endswith(".py")
                           and not n.startswith(outside)
                           and not n.endswith("__init__.py") and n not in listed]
                unboxed = [path for path in listed if not path.startswith(outside)
                           and not any(path.startswith(prefix) for prefix in owners)]
                stale = [path for path in listed if path not in present
                         and not any(n.startswith(path) for n in names if path.endswith("/"))]
                for count, what in ((missing, "src/ Python files missing from the file lists"),
                                    (unboxed, "listed paths in no map box"),
                                    (stale, "listed paths not in the repo")):
                    if count:
                        reasons.append(f"{len(count)} {what}: {', '.join(count[:5])}"
                                       + (" ..." if len(count) > 5 else ""))
            result["views"][view["id"]] = {"flagged": bool(reasons), "reasons": reasons,
                                           "moved": moved, "example_changed": sorted(changed)}
        return result
    finally:
        cat.stdin.close()
        cat.wait()


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, encoding="utf-8",
                          errors="replace", check=True).stdout


def payload(source: str) -> dict:
    body = "\n".join(line for line in source.splitlines()
                     if not line.startswith(("//", '"use strict"')))
    return json.loads(body[body.index("{"):body.rindex("}") + 1])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "how-code-works-files.js")
    args = parser.parse_args()
    view = payload((ROOT / f"{DIAGRAM_VIEW}map.js").read_text(encoding="utf-8"))
    owners = sorted(((prefix, box["id"]) for box in view["elements"]
                     for prefix in box.get("files", [])), key=lambda pair: -len(pair[0]))
    outside = tuple(view.get("outside", []))
    files = []
    for page, heading in DIAGRAM_LISTS.items():
        for path, text in file_list((ROOT / page).read_text(encoding="utf-8"), heading):
            if path.startswith(outside):
                continue
            box = next((owner for prefix, owner in owners if path.startswith(prefix)), None)
            files.append({"path": path, "text": " ".join(text.split()), "box": box,
                          "list": page})
    data = {"from": " and ".join(DIAGRAM_LISTS), "files": files}
    args.out.write_text(
        '"use strict";\n'
        "// Generated by scripts/diagram_files.py from the file lists; do not edit by hand.\n"
        f"Object.assign(DIAGRAM_FILES, {json.dumps(data, indent=1, ensure_ascii=False)});\n",
        encoding="utf-8")
    unboxed = [file["path"] for file in files if file["box"] is None]
    print(f"wrote {args.out}: {len(files)} paths, {len(unboxed)} in no box {unboxed}")


if __name__ == "__main__":
    main()
