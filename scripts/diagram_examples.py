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
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

from twwarhammer3.battle import replay

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = re.compile(r"/home/|\\\\home\\\\|C:\\\\Users|C:/Users|/mnt/c/Users|7656119\d{10}"
                     r"|[\w.+-]+@[\w-]+\.[\w.]+|sk-[A-Za-z0-9_-]{16,}|wrkspc_", re.I)
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
    # One decision, end to end: request 25 (state at 79.7 s, reply in row 99, applied 83.0 s).
    "decision": {
        "kind": "decision",
        "job": "runs/twwarhammer3/battle/bench-b45-knights3-glm-low-l1-20261020",
        "episode": "episode-0000",
        "results": "docs/twwarhammer3/results.csv",
        "decisions": ["r25", "r26"],
        "story": "docs/how-code-works-view-decision.js",
    },
    # Two scripted members, one army: the Team live check's probe 1 (the infantry member waits
    # 3 s on purpose), the battle the frozen Team tab's probe flow drew.
    "members": {
        "kind": "members",
        "job": "runs/twwarhammer3/team-live-20261031e/probe-1",
        "episode": "episode",
        "date": "2026-10-31",
        "decisions": ["r1", "r2", "r13", "r14", "r15", "r16", "r17"],  # r5, r6: the middle
        "story": "docs/how-code-works-view-members.js",
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
    routed = lambda unit: bool({"routing", "shattered"} & set(unit.get("state") or []))  # noqa: E731
    return [{"id": unit["id"], "side": side,
             "label": names.get(unit["id"], unit["id"]) + (", routing" if routed(unit) else ""),
             "routing": routed(unit),
             "x": round(unit["x"]), "z": round(unit["z"]),
             "bearing": round(unit.get("bearing") or 0),
             "men": unit.get("men"), "men0": unit.get("men0")}
            for side in ("friendly", "enemy") for unit in frame[side]
            if unit.get("x") is not None and unit.get("z") is not None]


def short(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit - 3].rstrip() + "..."


def cited_files(story_path: str, commit: str) -> tuple[dict, list]:
    story = payload((ROOT / story_path).read_text(encoding="utf-8"))
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
    return files, changed


def map_frame(frame: dict, names: dict, orders: list, note: str, source: str) -> dict:
    units = frame_units(frame, names)
    points = [(u["x"], u["z"]) for u in units] + [(o["x"], o["z"]) for o in orders]
    xs, zs = [p[0] for p in points], [p[1] for p in points]
    cx, cz = (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2
    half_x = max(60, (max(xs) - min(xs)) / 2 + 30)
    half_z = max(40, (max(zs) - min(zs)) / 2 + 30)
    return {"time_ms": frame["time_ms"], "units": units, "orders": orders, "note": note,
            "source": source, "bounds": [round(cx - half_x), round(cx + half_x),
                                         round(cz - half_z), round(cz + half_z)]}


def build_decision(recipe: dict, runs: Path) -> dict:
    """One decision: what the model saw, the prompt's parts, the call, the reply, the request,
    the acknowledgement and the next prompt's timing line, each from its own trace row."""
    job, episode = runs / recipe["job"], runs / recipe["job"] / recipe["episode"]
    manifest = json.loads((job / "manifest.json").read_text())
    data = replay.build(episode, manifest)
    names = {entry["id"]: label(entry) for entry in data["roster"]}
    by_request = {d["request"].rsplit("-", 1)[-1]: d for d in data["decisions"]}
    rows = {n: json.loads(line) for n, line in enumerate((episode / "trace.jsonl").open(), 1)}
    first, then = (by_request[r] for r in recipe["decisions"])
    basis, after = data["frames"][first["basis_frame"]], data["frames"][then["basis_frame"]]
    exchange_id = first["attempts"][-1]["exchange_id"]
    reply_row = next(n for n, r in rows.items() if r.get("kind") == "model_exchange"
                     and any(a.get("exchange_id") == exchange_id for a in r["attempts"]))
    next_id = then["attempts"][-1]["exchange_id"]
    next_row = next(n for n, r in rows.items() if r.get("kind") == "model_exchange"
                    and any(a.get("exchange_id") == next_id for a in r["attempts"]))
    attempt = rows[reply_row]["attempts"][-1]
    usage = attempt.get("usage") or {}
    ack_row = first["ack_source"]["line"]
    ack = rows[ack_row]
    path = f"{recipe['job']}/{recipe['episode']}/trace.jsonl"
    orders = [o["order"] for o in first["orders"]]
    saw = []
    for unit in frame_units(basis, names):
        state = next((u for side in ("friendly", "enemy") for u in basis[side]
                      if u["id"] == unit["id"]), {}).get("state") or []
        saw.append(f"{unit['label']}: x {unit['x']}, z {unit['z']}, {unit['men']} of "
                   f"{unit['men0']} men, {', '.join(state) or 'idle'}")
    parts, block = [], []  # parts split at blank lines and at heading lines ("Your units:")
    for line in rows[reply_row]["prompt"].splitlines() + [""]:
        if (not line.strip() or (line.rstrip().endswith(":") and block)) and block:
            head = block[0] + (" " + block[1] if block[0].endswith(":") and len(block) > 1
                               else "")
            parts.append(short(head, 110))
            block = []
        if line.strip():
            block.append(line)
    timing = [line for line in rows[next_row]["prompt"].splitlines()
              if "Your last batch" in line or line.startswith("Last orders")]
    kinds = []
    for n in range(reply_row, next_row + 2):
        row = rows[n]
        kind = row.get("kind")
        what = {"model_exchange": lambda r: f"model exchange {r['attempts'][-1]['exchange_id']}",
                "observation": lambda r: f"state seq {r['observation']['seq']} at "
                                         f"{seconds(r['observation']['time_ms'])}",
                "decision": lambda r: f"decision, request {r['request'].rsplit('-r', 1)[-1]}",
                "ack": lambda r: f"acknowledgement: applied at {seconds(r['ack']['applied_ms'])}"
                }.get(kind, lambda r: kind)(row)
        kinds.append(f"row {n}: {what}")
    messages = {
        "saw": {"title": f"What the model saw at {seconds(first['time_ms'])} (trace row "
                         f"{basis['source']['line']})",
                "text": "\n".join(saw), "source": f"{path} row {basis['source']['line']}"},
        "prompt": {"title": f"The prompt, first line of each part (trace row {reply_row})",
                   "text": "\n".join(parts[:10]), "source": f"{path} row {reply_row}"},
        "call": {"title": f"The call (trace row {reply_row})",
                 "text": "\n".join([
                     f"model {attempt['actual_model']} through {attempt['provider']}, "
                     f"backend {attempt['backend']}",
                     f"{usage.get('input_tokens')} tokens in "
                     f"({(usage.get('input_tokens_details') or {}).get('cached_tokens')} "
                     f"cached), {usage.get('output_tokens')} out",
                     f"{attempt['seconds']:.2f} s of WSL time, ${attempt['usd']:.4f}"]),
                 "source": f"{path} row {reply_row}"},
        "trace": {"title": f"The trace rows, written after the reply: no state between seq "
                           f"{first['seq']} and seq {then['seq']} was read",
                  "text": "\n".join(kinds),
                  "source": f"{path} rows {reply_row}-{next_row + 1}"},
        "reply": {"title": f"The model's reply (trace row {reply_row})",
                  "text": short(attempt["text"], 420), "source": f"{path} row {reply_row}"},
        "request": {"title": f"The request written to orders.json, shortened (trace row "
                             f"{first['source']['line']})",
                    "text": json.dumps({"request": "r" + first["request"].rsplit("-r", 1)[-1],
                                        "based_on": first["seq"],
                                        "orders": [{k: v for k, v in o.items() if v is not None}
                                                   for o in orders]}),
                    "source": f"{path} row {first['source']['line']} (request id shortened; "
                              "empty fields and schema, job and battle left out)"},
        "ack": {"title": f"The acknowledgement (trace row {ack_row})",
                "text": "\n".join([f"applied at {seconds(ack['ack']['applied_ms'])}, based on "
                                   f"state seq {ack['ack']['based_on']}",
                                   "results: " + ", ".join(
                                       f"{names.get(r['unit'], r['unit'])} "
                                       f"{'ok' if r['ok'] else 'refused'}"
                                       for r in ack["ack"]["results"]),
                                   f"delay {ack['latency']['delay_ms']} ms of battle time; "
                                   f"think {ack['latency']['think_s']} s of WSL time"]),
                "source": f"{path} row {ack_row}"},
        "next": {"title": f"The next prompt's timing lines (trace row {next_row})",
                 "text": "\n".join(short(line, 200) for line in timing),
                 "source": f"{path} row {next_row}"},
    }
    moves = [{"unit": o["unit"], "x": o["x"], "z": o["z"]} for o in orders if o["type"] == "move"]
    frames = {
        "saw": map_frame(basis, names, moves,
                         f"What the model saw at {seconds(first['time_ms'])}: our units blue, the "
                         "enemies our side could see red (a policy never sees the others); "
                         "dashed: the move it ordered. x right, z up.",
                         f"{path} row {basis['source']['line']}"),
        "after": map_frame(after, names, [],
                           f"The next state the model saw, at {seconds(then['time_ms'])}, when "
                           "the order had just been applied. x right, z up.",
                           f"{path} row {after['source']['line']}"),
    }
    files, changed = cited_files(recipe["story"], manifest["source_revision"])
    with (ROOT / recipe["results"]).open(newline="") as table:
        row = next(r for r in csv.DictReader(table) if r["job"] == Path(recipe["job"]).name
                   and r["episode"] == recipe["episode"])
    month = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()[int(row["date"][5:7]) - 1]
    return {"job": Path(recipe["job"]).name, "episode": recipe["episode"], "date": row["date"],
            "date_text": f"{int(row['date'][8:])} {month}",
            "commit": manifest["source_revision"][:7], "outcome": row["outcome"],
            "story": recipe["story"], "files": files, "changed_since": changed,
            "messages": messages, "frames": frames}


def build_members(recipe: dict, runs: Path) -> dict:
    """Two members sharing one army: the partition, an idle poll, each member's move and the
    alternation after, each from its own trace row (a scripted check: no model, no results row)."""
    job, episode = runs / recipe["job"], runs / recipe["job"] / recipe["episode"]
    manifest = json.loads((job / "manifest.json").read_text())
    data = replay.build(episode, manifest)
    names = {entry["id"]: label(entry) for entry in data["roster"]}
    rows = {n: json.loads(line) for n, line in enumerate((episode / "trace.jsonl").open(), 1)}
    by_request = {d["request"].rsplit("-", 1)[-1]: d for d in data["decisions"]}
    path = f"{recipe['job']}/{recipe['episode']}/trace.jsonl"
    split = next((n, r) for n, r in rows.items() if r.get("event") == "partition")
    start = data["frames"][by_request["r1"]["basis_frame"]]

    def member(request):
        return (rows[by_request[request]["source"]["line"]].get("behavior") or {}).get("member")

    def summary(request):
        d = by_request[request]
        orders = [o["order"] for o in d["orders"]]
        who = member(request)
        what = "; ".join(order_text({**o, "x": round(o["x"]), "z": round(o["z"])}
                                    if o.get("type") == "move" else o, names) for o in orders)
        return (f"request {request[1:]} (trace row {d['source']['line']}): "
                + (f"{who}'s batch: {what or 'no orders'}" if who else "idle poll, no orders")
                + (f"; applied at {seconds(d['applied_ms'])}" if d.get("applied_ms") else ""))

    def member_feedback(request):  # the team's feedback row for this request's member
        after = by_request[request]["ack_source"]["line"]
        return next((n, r) for n, r in rows.items() if n > after and r.get("event") == "feedback"
                    and r.get("member") == member(request))

    owners = split[1]["ownership"]
    messages = {
        "split": {"title": f"The team's partition (trace row {split[0]})",
                  "text": "\n".join(f"{who}: {names.get(unit, unit)}"
                                     for who, unit in owners.items()),
                  "source": f"{path} row {split[0]}"},
        "idle": {"title": "Two rounds in the middle", "text": summary("r5") + "\n"
                 + summary("r6"), "source": f"{path} rows {by_request['r5']['source']['line']} "
                                            f"and {by_request['r6']['source']['line']}"},
        "r2": {"title": "Cavalry's move goes alone", "text": summary("r2"),
               "source": f"{path} row {by_request['r2']['source']['line']}"},
        "r13": {"title": "Infantry's move, a round after it finished",
                "text": summary("r13") + f"\nthe team's feedback to infantry (trace row "
                        f"{member_feedback('r13')[0]}): order age "
                        f"{member_feedback('r13')[1]['latency']['delay_ms']} ms of battle time, "
                        f"from the state infantry decided on; think "
                        f"{member_feedback('r13')[1]['latency']['think_s']:.1f} s",
                "source": f"{path} rows {by_request['r13']['source']['line']} and "
                          f"{member_feedback('r13')[0]}"},
        "alternate": {"title": "Then the members alternate",
                      "text": "\n".join(summary(r) for r in recipe["decisions"][3:]),
                      "source": f"{path} decision rows"},
    }
    frames = {"start": map_frame(start, names, [],
                                 f"The units at {seconds(start['time_ms'])}: ours blue, the "
                                 "enemies our side could see red. x right, z up.",
                                 f"{path} row {start['source']['line']}")}
    for request, who in (("r2", "cavalry"), ("r13", "infantry")):
        moves = [{"unit": o["order"]["unit"], "x": round(o["order"]["x"]),
                  "z": round(o["order"]["z"])} for o in by_request[request]["orders"]]
        frames[who] = map_frame(start, names, moves,
                                f"The units at {seconds(start['time_ms'])}, the state both members "
                                f"started from; dashed: {who}'s move. x right, z up.",
                                f"{path} row {start['source']['line']}")
    files, changed = cited_files(recipe["story"], manifest["source_revision"])
    month = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()[int(recipe["date"][5:7]) - 1]
    return {"job": f"{Path(recipe['job']).parent.name}/{Path(recipe['job']).name}",
            "episode": recipe["episode"], "date": recipe["date"],
            "date_text": f"{int(recipe['date'][8:])} {month}",
            "commit": manifest["source_revision"][:7], "outcome": "a scripted live check",
            "story": recipe["story"], "files": files, "changed_since": changed,
            "messages": messages, "frames": frames}


def build(recipe: dict, runs: Path) -> dict:
    if recipe.get("kind") == "members":
        return build_members(recipe, runs)
    if recipe.get("kind") == "decision":
        return build_decision(recipe, runs)
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
    exchanges = {}  # exchange id -> its model_exchange row (1-based), the model's reply
    for number, line in enumerate((episode / "trace.jsonl").open(), 1):
        if '"kind": "model_exchange"' in line:
            row = json.loads(line)
            for attempt in row.get("attempts", []):
                exchanges[attempt.get("exchange_id")] = number
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
        reply = exchanges.get((decision.get("attempts") or [{}])[-1].get("exchange_id"))
        messages[request] = {"title": f"The decision, request {request[1:]} (trace row {row}; "
                                      f"the model's reply is row {reply})",
                             "text": "\n".join(lines),
                             "source": f"{recipe['job']}/{recipe['episode']}/trace.jsonl rows "
                                       f"{basis['source']['line']} and {row}"}
        frames[request] = {
            "time_ms": decision["time_ms"],
            "units": frame_units(basis, names),
            "orders": [{"unit": o["unit"], "x": o["x"], "z": o["z"]} for o in orders
                       if o.get("type") == "move"],
            "note": f"What the model saw at {seconds(decision['time_ms'])}: our units blue, the "
                    "enemies our side could see red (a policy never sees the others)"
                    + ("; dashed: a move order" if any(o.get("type") == "move" for o in orders)
                       else "") + ". x right, z up.",
            "source": f"{recipe['job']}/{recipe['episode']}/trace.jsonl row "
                      f"{basis['source']['line']}"}
    with (ROOT / recipe["results"]).open(newline="") as table:
        number, row = next((i + 2, row) for i, row in enumerate(csv.DictReader(table))
                           if row["job"] == Path(recipe["job"]).name
                           and row["episode"] == recipe["episode"])
    messages["row"] = {"title": f"The results.csv row (line {number})",
                       "text": "\n".join(f"{key}: {row[key]}" for key in ROW_FIELDS),
                       "source": f"{recipe['results']} line {number}"}
    report = (runs / recipe["report"]).read_text().splitlines()
    table = [line for line in report if line.startswith(("Scenario:", "| Controller", "| llm"))]
    messages["report"] = {
        "title": "The report built for this page (the job is not in benchmark_jobs.json)",
        "text": "twwarhammer3 report JOB --output NAME\n" + "\n".join(table[:3]),
        "source": f"{recipe['report']}, built on 2026-11-01"}
    frames["start"] = {**frames[recipe["decisions"][0]], "orders": [],
                       "note": f"The battle at {seconds(first['time_ms'])}, as the model first "
                               "saw it: our units blue, the enemies our side could see red. "
                               "x right, z up."}
    for frame in frames.values():  # each map is scaled to its own units, at least 120 x 80 m
        points = [(u["x"], u["z"]) for u in frame["units"]]
        points += [(o["x"], o["z"]) for o in frame["orders"]]
        xs, zs = [p[0] for p in points], [p[1] for p in points]
        cx, cz = (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2
        half_x = max(60, (max(xs) - min(xs)) / 2 + 30)
        half_z = max(40, (max(zs) - min(zs)) / 2 + 30)
        frame["bounds"] = [round(cx - half_x), round(cx + half_x), round(cz - half_z),
                           round(cz + half_z)]
    month = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()[int(row["date"][5:7]) - 1]
    return {"job": Path(recipe["job"]).name, "episode": recipe["episode"],
            "date": row["date"], "date_text": f"{int(row['date'][8:])} {month}",
            "commit": commit[:7], "outcome": row["outcome"], "story": recipe["story"],
            "files": files, "changed_since": changed,
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
