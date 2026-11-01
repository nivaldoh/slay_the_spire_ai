"""Copy small excerpts of a recorded battle into docs/how-code-works-example-<id>.js.

The owner's answer 3a (2026-11-01, docs/how-code-works-plan.md section 3): a story's examples are
copied from a recorded battle by a script, never typed, and committed in docs/ (public), as a
standing exception to "run evidence stays out of Git", for small excerpts only.

    uv run --locked python scripts/diagram_examples.py job [--runs MAIN_CHECKOUT]

It reads the main checkout's runs/ read-only through twwarhammer3.battle.replay.build(), as the
offline report does, and copies only listed fields: manifests, results, environment.json and
game.log also hold home paths, a Windows username and a Steam ID. It refuses to write output that
matches one of PRIVATE. What the model saw is the decision's basis frame (a trace observation),
never the 1 Hz recorder frames, whose enemy lists were not checked against what the side could see.
Trace rows are 1-based lines of trace.jsonl, as build() numbers them.

Each excerpt names its job, its battle's commit and the code files its story cites (under src/,
configs/ and scripts/), each with its sha256 at that commit. changed_since lists the cited files
whose content at HEAD differs: the page's "code changed since" badge (plan section 3).
scripts/check.py flags the story when another cited file changes later. Output depends only on the
recorded files, the story file and HEAD's copies of the cited files, so two runs at one revision
write identical files. Modelled on scripts/diagram_replay.py.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from twwarhammer3.battle import replay

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = re.compile(r"/home/|C:\\\\Users|C:/Users|/mnt/c/Users|7656119\d{10}"
                     r"|[\w.+-]+@[\w-]+\.[\w.]+|sk-[A-Za-z0-9_-]{16,}", re.I)
# JUDGEMENT?: Example choices (Claude Code, 2026-11-01): the battle and its three decisions
# (plan, Knights pulled out, last order). Other decisions would tell a different story; the
# "One play job" story's messages and maps rest on these.
EXAMPLES = {
    "job": {
        "job": "runs/twwarhammer3/battle/bench-b45-knights3-glm-low-l1-20261020",
        "episode": "episode-0000",
        "plan": "runs/twwarhammer3/calibration/empire-20261020/plan-d.json",
        "report": "runs/how-code-works-20261101/report/knights3.txt",
        "results": "docs/twwarhammer3/results.csv",
        "decisions": ["r1", "r25", "r88"],
        "story": "docs/how-code-works-view-job.js",
    },
}
ROW_FIELDS = ("date", "job", "scenario", "policy", "model", "effort", "provider", "source",
              "outcome", "battle_s", "own_left", "enemy_left", "decisions", "invalid", "delay_s",
              "usd", "ended_by")


def main_checkout() -> Path:
    common = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                            cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    return Path(common).parent


def git_blob(rev: str, path: str) -> bytes | None:
    done = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=ROOT, capture_output=True)
    return done.stdout if done.returncode == 0 else None


def payload(source: str) -> dict:
    body = "\n".join(line for line in source.splitlines()
                     if not line.startswith(("//", '"use strict"')))
    return json.loads(body[body.index("{"):body.rindex("}") + 1])


def seconds(ms) -> str:
    return f"{ms / 1000:.1f} s"


def label(entry: dict) -> str:
    name = entry["display"].removeprefix("Empire ")
    return f"{name} ({entry['id']})"


def order_text(order: dict, names: dict) -> str:
    unit = names.get(order.get("unit"), order.get("unit"))
    if order.get("type") == "move":
        return (f"move {unit} to x {order['x']}, z {order['z']}"
                + (", running" if order.get("run") else ""))
    if order.get("type") == "attack":
        return f"{unit} attacks {names.get(order['target'], order['target'])}" + (
            f" ({order['mode']})" if order.get("mode") else "")
    return json.dumps(order, sort_keys=True)


def frame_units(frame: dict, names: dict) -> list[dict]:
    return [{"id": unit["id"], "side": side, "label": names.get(unit["id"], unit["id"]),
             "x": round(unit["x"]), "z": round(unit["z"]),
             "bearing": round(unit.get("bearing") or 0),
             "men": unit.get("men"), "men0": unit.get("men0")}
            for side in ("friendly", "enemy") for unit in frame[side]
            if unit.get("x") is not None and unit.get("z") is not None]


def build(recipe: dict, runs: Path) -> dict:
    job = runs / recipe["job"]
    episode = job / recipe["episode"]
    manifest = json.loads((job / "manifest.json").read_text())
    data = replay.build(episode, manifest)
    names = {entry["id"]: label(entry) for entry in data["roster"]}
    by_request = {d["request"].rsplit("-", 1)[-1]: d for d in data["decisions"]}
    commit = manifest["source_revision"]
    story = payload((ROOT / recipe["story"]).read_text(encoding="utf-8"))
    items = [story, *story["elements"], *story["wires"],
             *(step for flow in story["flows"] for step in flow["steps"])]
    cited = sorted({ref.split(":")[0] for item in items for ref in item.get("refs") or []
                    if ref.startswith(("src/", "configs/", "scripts/"))})
    files, changed = {}, []
    for path in cited:
        then, now = git_blob(commit, path), git_blob("HEAD", path)
        files[path] = hashlib.sha256(then).hexdigest() if then is not None else "absent"
        if then is None or now is None or then != now:
            changed.append(path)
    messages, frames = {}, {}
    plan = json.loads((runs / recipe["plan"]).read_text())
    entry = next(j for j in plan["jobs"] if j["output"] == recipe["job"])
    messages["command"] = {
        "title": f"The job's entry in the queue plan ({Path(recipe['plan']).name})",
        "text": "uv run python -m twwarhammer3 play \\\n  " + " ".join(entry["args"])
                + f" \\\n  --output {entry['output']}",
        "source": f"{recipe['plan']}, the job's args and output"}
    scenario, checks = manifest["scenario"], manifest["setup_checks"]
    messages["setup"] = {
        "title": "The scenario and the setup checks (manifest.json)",
        "text": "\n".join([scenario["brief"].split(". ")[0] + ".",
                           f"difficulty: {checks['difficulty']}",
                           f"funds: {checks['funds_amount']}",
                           f"battle type: {checks['battle_type']}; time limit "
                           f"{checks['time_limit_s']} s"]),
        "source": f"{recipe['job']}/manifest.json: scenario.brief and setup_checks"}
    first = data["frames"][by_request[recipe["decisions"][0]]["basis_frame"]]
    messages["start"] = {
        "title": f"The units at {seconds(first['time_ms'])} ({first['source']['file']} row "
                 f"{first['source']['line']})",
        "text": "\n".join(f"{u['label']}: {u['men']} of {u['men0']} men"
                          for u in frame_units(first, names)),
        "source": f"{recipe['job']}/{recipe['episode']}/trace.jsonl row {first['source']['line']}"}
    for request in recipe["decisions"]:
        decision = by_request[request]
        basis = data["frames"][decision["basis_frame"]]
        row = decision["source"]["line"]
        orders = [o["order"] for o in decision["orders"]]
        lines = [f"State it saw: {seconds(decision['time_ms'])} (trace row "
                 f"{basis['source']['line']})"]
        if decision.get("applied_ms") is not None:
            lines.append(f"Applied in the game: {seconds(decision['applied_ms'])}, "
                         f"{seconds(decision['applied_ms'] - decision['time_ms'])} later")
        lines.append(f"Reason: \"{decision['reason']}\"")
        lines.append("Orders: " + ("; ".join(order_text(o, names) for o in orders) or "none"))
        messages[request] = {"title": f"The model's reply, request {request[1:]} "
                                      f"(trace row {row})",
                             "text": "\n".join(lines),
                             "source": f"{recipe['job']}/{recipe['episode']}/trace.jsonl rows "
                                       f"{basis['source']['line']} and {row}"}
        frames[request] = {
            "time_ms": decision["time_ms"],
            "units": frame_units(basis, names),
            "orders": [{"unit": o["unit"], "x": o["x"], "z": o["z"]} for o in orders
                       if o.get("type") == "move"],
            "note": f"What the model saw at {seconds(decision['time_ms'])}: our units blue, the "
                    "enemies our side could see red (a policy never sees the others); dashed: a "
                    "move order. x right, z up.",
            "source": f"{recipe['job']}/{recipe['episode']}/trace.jsonl row "
                      f"{basis['source']['line']}"}
    header, *rows = (ROOT / recipe["results"]).read_text().splitlines()
    keys = header.split(",")
    number, row = next((i + 2, dict(zip(keys, line.split(",")))) for i, line in enumerate(rows)
                       if f",{Path(recipe['job']).name},{recipe['episode']}," in line)
    messages["row"] = {"title": f"The results.csv row (line {number})",
                       "text": "\n".join(f"{key}: {row[key]}" for key in ROW_FIELDS),
                       "source": f"{recipe['results']} line {number}"}
    report = (runs / recipe["report"]).read_text().splitlines()
    table = [line for line in report if line.startswith(("Scenario:", "| Controller", "| llm"))]
    messages["report"] = {
        "title": "The report built for this page (the job is not in benchmark_jobs.json)",
        "text": "twwarhammer3 report JOB --output NAME\n" + "\n".join(table[:3]),
        "source": f"{recipe['report']}, built on 2026-11-01"}
    points = [(u["x"], u["z"]) for f in frames.values() for u in f["units"]]
    points += [(o["x"], o["z"]) for f in frames.values() for o in f["orders"]]
    xs, zs = [p[0] for p in points], [p[1] for p in points]
    month = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()[int(row["date"][5:7]) - 1]
    return {"job": Path(recipe["job"]).name, "episode": recipe["episode"],
            "date": row["date"], "date_text": f"{int(row['date'][8:])} {month}",
            "commit": commit[:7], "outcome": row["outcome"], "story": recipe["story"],
            "files": files, "changed_since": changed,
            "bounds": [min(xs) - 40, max(xs) + 40, min(zs) - 40, max(zs) + 40],
            "messages": messages, "frames": frames}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("example", choices=sorted(EXAMPLES))
    parser.add_argument("--runs", type=Path, help="the checkout whose runs/ to read "
                        "(default: the main checkout)")
    args = parser.parse_args()
    example = build(EXAMPLES[args.example], args.runs or main_checkout())
    text = (f'"use strict";\n// Generated by scripts/diagram_examples.py {args.example}; do not '
            f"edit by hand.\nObject.assign(DIAGRAM_EXAMPLES, "
            f"{json.dumps({args.example: example}, indent=1, ensure_ascii=False)});\n")
    leak = PRIVATE.search(text)
    if leak:
        raise SystemExit(f"refused: the output matches a private pattern near {leak.start()}")
    out = ROOT / "docs" / f"how-code-works-example-{args.example}.js"
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}: {len(text.encode())} bytes, "
          f"{len(example['changed_since'])} of {len(example['files'])} cited files changed since "
          f"{example['commit']}")


if __name__ == "__main__":
    main()
