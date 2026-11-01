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

Two kinds read GaP battles (docs/how-code-works-plan.md, the control-methods spec's generated
data): `methods` writes the "Control methods" lanes, side cells and card numbers, one example per
method plus "methods" (lanes and cards); `graph` writes the boxes and wires of the recorded graphs
for "One graph battle". Both read graph steps through twwarhammer3.battle.graph_view.
collect_episode(), which checks every member_event against the recorded graphs, and trace rows
for each member's own view. They recompute every count in the recipe's `stated` and refuse to
write when one differs; `stated` is meant to hold each record count the story states (its
captions, labels, summary and notes, not its status lines). One methods view cites both methods'
code, so each methods example takes its files from its group's `refs`; graph takes them from its
story's refs (the recipe's `refs` while the story file does not exist yet) plus the generated
boxes' refs.
"""
import argparse
import ast
import csv
import hashlib
import json
import re
import statistics
import subprocess
import textwrap
from collections import Counter
from functools import cache
from math import hypot
from pathlib import Path

from twwarhammer3.battle import graph_view, replay

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
    # JUDGEMENT?: Example battles (Claude Code, 2026-11-01): knights3 for basic, gap-initial-02
    # for GaP (also the graph recipe): one battle each, both lost, same scenario, other revisions.
    # bench-b45-line-xp5 or a v4 GaP battle would change every number, map and caption below.
    # JUDGEMENT?: Methods window (Claude Code, 2026-11-01): battle 5.3-35.3 s, the first 30 s.
    # A window around first contact (GaP 334.7 s) is busier for both; what the strip teaches
    # rests on it (2 of 9 replies new; the cavalry only says "no").
    # JUDGEMENT?: Resent rule (Claude Code, 2026-11-01): a batch equal to that member's previous
    # non-empty batch is "sent again". The unit's current engine order, or no split, would move
    # the new/resent marks and card counts (basic 28 new of 39, GaP 6 of 165).
    # Texts here are hand-written (control-methods spec, card fields and side cells); `stated`
    # holds every count a caption or label states, and the build refuses when one differs.
    "methods": {
        "kind": "methods",
        "story": "docs/how-code-works-view-methods.js",
        "results": "docs/twwarhammer3/results.csv",
        "window": [5300, 35300],
        "groups": [
            {"id": "basic", "kind": "model", "example": "methods-basic",
             "job": "runs/twwarhammer3/battle/bench-b45-knights3-glm-low-l1-20261020",
             "episode": "episode-0000",
             "title": "Basic: the model picks every order", "where": "in the loop",
             "code": "llm_rules · battle/llm.py",
             "before": "Nothing asked: the rules prompt is written by hand",
             "between": "Nothing: a fresh controller each battle, same prompt",
             "decisions": ["r1", "r2"],  # reply 1 and its ack, reply 2 (methods steps 1-3)
             "refs": ["src/twwarhammer3/battle/play.py:1-17",
                      "src/twwarhammer3/battle/play.py:501-503",
                      "src/twwarhammer3/battle/controllers.py:28-32",
                      "src/twwarhammer3/battle/controllers.py:35-50",
                      "src/twwarhammer3/battle/llm.py:59-82",
                      "src/twwarhammer3/battle/llm.py:464-478"],
             "stated": {"calls": [0, 92, 0], "decisions": 88, "reasks": 3, "unused_calls": 1,
                        "carried": 39, "new": 28,
                        "replies_in_window": 9, "new_in_window": 2, "first_view_ms": 5300,
                        "first_applied_ms": 8900, "delay_ms": [3300, 1800, 18000]}},
            {"id": "gap", "kind": "graph", "example": "methods-gap",
             "job": "runs/twwarhammer3/battle/gap-initial-02-20261101", "episode": "episode-0000",
             "artifact": "runs/twwarhammer3/gap-20261101/initial-02",
             "revisions": ["runs/twwarhammer3/gap-20261101/revised-01"],
             "title": "GaP: models write graphs, code plays them",
             "where": "before and between battles", "code": "configured · battle/graph.py",
             "empty": "no model asked during the battle",
             "members": {"cavalry": "A", "line": "B"},  # page colours: A blue, B vermillion
             "rows": {"steps": [37, 28], "order": 75, "view": 66},  # methods steps 5 and 6
             "refs": ["src/twwarhammer3/battle/play.py:1-17",
                      "src/twwarhammer3/battle/play.py:501-503",
                      "src/twwarhammer3/battle/controllers.py:28-32",
                      "src/twwarhammer3/battle/controllers.py:35-50",
                      "src/twwarhammer3/battle/configured.py",
                      "src/twwarhammer3/battle/team.py:312-344",
                      "src/twwarhammer3/battle/graph.py:21-23",
                      "src/twwarhammer3/battle/graph.py:163-230",
                      "src/twwarhammer3/battle/skill_contracts.py:17-22",
                      "src/twwarhammer3/battle/skill_contracts.py:119-122",
                      "src/twwarhammer3/battle/graph_author.py:21",
                      "src/twwarhammer3/battle/graph_author.py:30-40",
                      "src/twwarhammer3/battle/graph_author.py:173-178"],
             "stated": {"calls": [3, 0, 3], "trace_model_exchanges": 0, "decisions": 2016,
                        "carried": 165, "new": 6, "resent_in_window": 11, "new_in_window": 1,
                        "first_view_ms": 7400, "first_applied_ms": 8000,
                        "resend_every_ms": 2400, "resend_range_ms": [2100, 2400], "author_s": 20,
                        "changed_members": ["cavalry"],
                        "cavalry_ticks": 50, "delay_ms": [600, 600, 900],
                        "revision_orders_match": True}},
        ],
    },
    # JUDGEMENT?: Graph story moments (Claude Code, 2026-11-01): the 8 steps from authoring to the
    # 386.3 s witness, from the rows below. The cavalry's charge failures after 407.9 s or the
    # line's later fights would tell another story; the graph view's steps rest on these rows.
    # The battle rests on JUDGEMENT? Example battles above; hiding unvisited steps and untaken
    # exits rests on JUDGEMENT? GaP drawn in the page (docs/multi-agent.html, by TAB_ORDER).
    "graph": {
        "kind": "graph",
        "job": "runs/twwarhammer3/battle/gap-initial-02-20261101",
        "episode": "episode-0000",
        "artifact": "runs/twwarhammer3/gap-20261101/initial-02",
        "results": "docs/twwarhammer3/results.csv",
        "story": "docs/how-code-works-view-graph.js",
        "members": {"cavalry": "A", "line": "B"},  # one row each, top to bottom
        # Rows sit in the view's WSL band, between its Cloud API band (left) and Windows band
        # (right): rests on JUDGEMENT? docs/how-code-works-view-graph.js Graph battle layout.
        # `arc` lifts each exit to the next box above its row (its label clears both boxes);
        # `bend` per box skipped sends other exits below the row.
        "layout": {"x": 240, "step": 186, "y": [76, 256], "w": 160, "h": 52, "arc": -80,
                   "bend": 40},
        # walk and melee_view are views given to the cavalry (the team input row before each names
        # it; team.py:312-344); melee_view is the first melee view, and the line judged engage
        # done from its next view.
        "rows": {"start": 6, "line": [14, 37, 55, 72], "view": 66, "order": 75, "contact": 28,
                 "walk": 4362, "deadline_view": 1651, "melee_view": 8722, "melee": 8737,
                 "charge": [8729, 8746, 8764, 8784], "charge_view": 8775, "witness_view": 10072,
                 "witness": 10078},
        # The story's refs while docs/how-code-works-view-graph.js does not exist yet.
        "refs": ["src/twwarhammer3/battle/graph.py:21-23",
                 "src/twwarhammer3/battle/graph.py:163-230",
                 "src/twwarhammer3/battle/team.py:312-344",
                 "src/twwarhammer3/battle/skill_contracts.py:17-22",
                 "src/twwarhammer3/battle/skill_contracts.py:119-122",
                 "src/twwarhammer3/battle/graph_author.py:21",
                 "src/twwarhammer3/battle/graph_author.py:30-40",
                 "src/twwarhammer3/battle/graph_view_assets/view.js:5-20",
                 "src/twwarhammer3/battle/graph_view_assets/view.js:88-99"],
        # The generated boxes' and exits' status, from the agreed check WH3 initial GaP (lines
        # 72-88 at 7e3892f and ad43a37): its live run at d12be58 witnessed contact and the
        # charge's melee; the other steps rest on its offline cases.
        "status": {"live_ops": ["contact", "charge"],
                   "live": {"text": "agreed live check: WH3 initial GaP, live 3/3 at d12be58 "
                                    "(contact and charge with melee witnesses); 91 offline cases "
                                    "at d6dfe92; holds and firing unchecked",
                            "refs": ["docs/agreed-checks.md:72-88"]},
                   "offline": {"text": "agreed offline check: WH3 initial GaP, 91 component cases "
                                       "(branches/loops, effect-based completion) at d6dfe92; the "
                                       "live run at d12be58 witnessed only contact and charge",
                               "refs": ["docs/agreed-checks.md:72-82",
                                        "docs/agreed-checks.md:87-88"]}},
        "stated": {"calls": 3, "author_s": 20, "before_usd": 0.0025, "battle_ms": 618200,
                   "outcome": "lost", "boxes": 8, "hidden_exits": 9,
                   "hidden_steps": ["line.wait"],
                   "hidden_by_status": {"empty": 5, "cancelled": 2, "yes": 1, "no": 1},
                   "hidden_unran_exits": {"line.wait": ["yes", "no"]},
                   "line_first_ms": 5300, "line_target": "e2", "applied_ms": 8000,
                   "no_before_contact": 542, "contact_ms": 334700, "timeout_s": 60,
                   "deadlines_before_contact": 5, "charge_order_ms": 336800,
                   "witness_ms": 386300, "witness_distance_m": 129,
                   "exits": {"cavalry.start>start": "no ×542", "cavalry.start>own": "yes ×1",
                             "cavalry.own>sel": "succeeded ×65",
                             "cavalry.sel>charge": "succeeded ×65",
                             "cavalry.charge>own": "succeeded ×61 / failed ×4",
                             "line.acquire>select": "succeeded ×85",
                             "line.select>refresh": "succeeded ×85",
                             "line.refresh>attack": "succeeded ×85",
                             "line.attack>acquire": "succeeded ×77 / failed ×7"}},
    },
}
CONTROLLERS = "src/twwarhammer3/battle/controllers.py"
AUTHOR = "src/twwarhammer3/battle/graph_author.py"
SKILLS = "src/twwarhammer3/battle/skill_contracts.py"
VIEW_JS = "src/twwarhammer3/battle/graph_view_assets/view.js"  # graph-view's labels and order
LABEL_REF, ORDER_REF = f"{VIEW_JS}:5-20", f"{VIEW_JS}:88-99"
STEP_REF, LIMIT_REF = "src/twwarhammer3/battle/graph.py:21-23", f"{SKILLS}:17-22"
DEADLINE_REF = f"{SKILLS}:103-105"  # a skill step fails at its deadline without its witness
WITNESS = {"engage": "melee", "charge": "melee", "move": "arrival", "hold": "arrival",
           "shoot": "ammo falling"}  # what each skill waits for (skill_contracts.py:107-122)
SHORT_ROLE = {"coordinator": "co", "cavalry": "cav"}  # block labels in the side cells
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
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


def clip(text: str, limit: int) -> str:  # short() that cuts at a space
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit - 4].rsplit(" ", 1)[0] + " ..."


def story_refs(story_path: str) -> list[str]:
    story = payload((ROOT / story_path).read_text(encoding="utf-8"))
    items = [story, *story["elements"], *story["wires"],
             *(step for flow in story["flows"] for step in flow["steps"])]
    return [ref for item in items for ref in item.get("refs") or []]


def cited_files(story_path: str, commit: str, refs: list | None = None) -> tuple[dict, list]:
    """The cited code files' sha256 at `commit`, and those changed at HEAD: the story's refs,
    or `refs` when given."""
    cited = sorted({ref.split(":")[0] for ref in (story_refs(story_path) if refs is None else refs)
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


def check_counts(name: str, stated: dict, found: dict) -> None:
    """Print every recomputed count; refuse when one a caption or label states differs."""
    wrong = [key for key in stated if key not in found or found[key] != stated[key]]
    for key, value in found.items():
        mark = ("" if key not in stated else " (stated, ok)" if key not in wrong
                else f" (MISMATCH: stated {stated[key]!r})")
        print(f"  {name} {key}: {value!r}{mark}")
    if wrong:
        raise SystemExit(f"refused: {name} disagrees with the record on {', '.join(wrong)}")


def head_constant(path: str, name: str, rev: str = "HEAD"):
    """A module-level literal, read by ast from the file at `rev`."""
    for node in ast.parse(git_blob(rev, path) or b"").body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name
                                                for t in node.targets):
            return ast.literal_eval(node.value)
    raise SystemExit(f"refused: no literal {name} in {path} at {rev}")


def results_line(results: str, job: str, episode: str) -> tuple[int, dict]:
    with (ROOT / results).open(newline="") as table:
        return next((i + 2, row) for i, row in enumerate(csv.DictReader(table))
                    if row["job"] == job and row["episode"] == episode)


def day_text(date: str) -> str:
    return f"{int(date[8:])} {MONTHS[int(date[5:7]) - 1]}"


def model_name(model: str) -> str:  # "z-ai/glm-5.3" -> "GLM 5.3"; "claude-haiku-5-5" -> "Haiku 5.5"
    head, *rest = model.split("/")[-1].removeprefix("claude-").split("-")
    return f"{head.upper() if len(head) <= 3 else head.title()} {'.'.join(rest)}"


def spread(values: list) -> list:  # median, min, max
    return [statistics.median(values), min(values), max(values)]


@cache
def recorded_cards(runs: Path) -> tuple:
    """(job, episode, card) of every recorded battle under runs/twwarhammer3/battle/; only the
    card is kept."""
    found = []
    for path in sorted((runs / "runs/twwarhammer3/battle").glob("*/episode-*/result.json")):
        card = json.loads(path.read_text()).get("card") or {}
        found.append((path.parent.parent.name, path.parent.name, card))
    return tuple(found)


def header(group: dict, calls: list) -> dict:  # a group's header row; its click opens the card
    return {"id": group["id"], "label": f"{group['title']} · {group['where']} · model calls "
                                        f"{' / '.join(map(str, calls))}",
            "header": True, "code": group["code"], "badges": [group["example"]],
            "card": group["id"]}


def view_age(delays: list) -> str:  # card field (7); delay_ms rests on JUDGEMENT Delay (play.py)
    return (f"Orders used a view {statistics.median(delays) / 1000:.1f} s old: median of "
            f"{len(delays)}, range {min(delays) / 1000:.1f}-{max(delays) / 1000:.1f} s, in battle "
            "time (result.json delays_ms; empty batches included)")


def battle_fields(group: dict, results: str, story: str, commit: str,
                  refs: list) -> tuple[dict, int, dict]:
    """The fields every example keeps (job, date, commit, files ...) and its results.csv row."""
    number, row = results_line(results, Path(group["job"]).name, group["episode"])
    files, changed = cited_files(story, commit, refs)
    return ({"job": Path(group["job"]).name, "episode": group["episode"], "date": row["date"],
             "date_text": day_text(row["date"]), "commit": commit[:7], "outcome": row["outcome"],
             "story": story, "files": files, "changed_since": changed}, number, row)


def graph_labels() -> tuple[dict, str, set]:
    """graph-view's plain step labels, its 'Choose enemy in melee' rule and its skill ops, read
    from view.js at HEAD (view.js:4-20), so the page's labels cannot drift unnoticed."""
    text = git_blob("HEAD", VIEW_JS).decode()
    block = text[text.index("const labels = {"):]
    labels = dict(re.findall(r'^\s*(\w+): "([^"]+)",?$', block[:block.index("};")], re.M))
    engaged = re.search(r'node\.mode === "engaged"\s*\?\s*"([^"]+)"', text)[1]
    skills = set(re.findall(r'"(\w+)"', re.search(r"skillOps = new Set\(\[([^\]]+)\]", text)[1]))
    return labels, engaged, skills


def node_label(node: dict, labels: tuple) -> str:  # graph-view's nodeLabel (view.js:16-20)
    return labels[1] if node["op"] == "select_target" and node.get("mode") == "engaged" else (
        labels[0].get(node["op"], node["op"]))


def graph_order(spec: dict) -> list[str]:
    """graph-view's depth-first order from the entry, succeeded and yes first (view.js:88-99)."""
    names: list[str] = []

    def visit(name):
        if name not in names:
            names.append(name)
            exits = spec["nodes"][name]["next"]
            for key in ("succeeded", "yes", *exits):
                if exits.get(key):
                    visit(exits[key])
    visit(spec["entry"])
    return names


def exit_order(node: dict) -> list[str]:  # graph-view's exit order, without repeats
    return list(dict.fromkeys(key for key in ("succeeded", "yes", *node["next"])
                              if key in node["next"]))


def outcome(record: dict) -> str:  # a step's result as the page says it: "f1", "e2", "no"
    values = [", ".join(v) if isinstance(v, list) else str(v)
              for v in (record.get("outputs") or {}).values()]
    return ", ".join(values) or record["status"]


def inputs_text(inputs: dict) -> str:
    return ", ".join(f"{key} {', '.join(v) if isinstance(v, list) else v}"
                     for key, v in sorted(inputs.items()))


def orders_text(orders: list, names: dict) -> str:
    return "; ".join(order_text(o, names) + (", running" if o.get("run") and
                                             o.get("type") == "attack" else "") for o in orders)


def trace_frame(data: dict, line: int) -> dict:
    """The public frame of one trace observation row (never a recorder frame)."""
    frame = next((f for f in data["frames"] if f["source"] == {"file": "trace.jsonl",
                                                              "line": line}), None)
    if frame is None:
        raise SystemExit(f"refused: trace row {line} is not an observation")
    return frame


def unit_of(frame: dict, uid: str) -> dict:
    return next(u for side in ("friendly", "enemy") for u in frame[side] if u["id"] == uid)


def apart(frame: dict, a: str, b: str) -> int:  # metres between two unit centres in one frame
    one, two = unit_of(frame, a), unit_of(frame, b)
    return round(hypot(one["x"] - two["x"], one["z"] - two["z"]))


def aim(frame: dict, unit: str, target: str) -> dict:  # a dashed map line from unit to target
    other = unit_of(frame, target)
    return {"unit": unit, "x": round(other["x"]), "z": round(other["z"])}


def spot(frame: dict, uid: str, names: dict) -> str:  # "Knights (f2) 90, -282: idle"
    unit = unit_of(frame, uid)
    return (f"{names[uid]} {round(unit['x'])}, {round(unit['z'])}: "
            f"{', '.join(unit.get('state') or []) or 'idle'}"
            + (f", target {unit['target']}" if unit.get("target") else ""))


def lines(*texts: str, most: int = 9) -> str:
    """A message beside a map: lines of at most 44 characters (the panel's width at 1366x768),
    continued lines indented, and at most `most` of them, so the box never needs scrolling.
    The texts are searched for PRIVATE before wrapping: a wrap can split a long path or key."""
    if any(PRIVATE.search(text) for text in texts):
        raise SystemExit("refused: a message matches a private pattern")
    out = [part for text in texts for part in textwrap.wrap(
        text, 44, subsequent_indent="  ", break_on_hyphens=False)]
    if len(out) > most:
        raise SystemExit(f"refused: a message of {len(out)} lines, over {most}: {out[0]}")
    return "\n".join(out)


class GaP:
    """One recorded GaP battle: its graphs and steps (graph_view.collect_episode), trace rows,
    public frames (replay.build), the artifact that wrote its graphs and the revisions made from
    its record. Every lookup refuses when a row is not what the caller names."""

    def __init__(self, group: dict, runs: Path):
        self.group, self.runs = group, runs
        job, episode = runs / group["job"], runs / group["job"] / group["episode"]
        self.path = f"{group['job']}/{group['episode']}/trace.jsonl"
        self.manifest = json.loads((job / "manifest.json").read_text())
        self.result = json.loads((episode / "result.json").read_text())
        self.data = replay.build(episode, self.manifest)
        self.names = {entry["id"]: label(entry) for entry in self.data["roster"]}
        self.view = graph_view.collect_episode(episode)
        self.rows = {n: json.loads(line) for n, line in enumerate((episode / "trace.jsonl")
                                                                 .open(), 1)}
        self.acks = {r["request"]: n for n, r in self.rows.items() if r.get("kind") == "ack"}
        self.labels = graph_labels()
        self.commit = self.manifest["source_revision"]
        disclosure = self.result["card"]["disclosure"]
        sha = disclosure["artifact"]["controller_sha256"]
        directory = runs / group["artifact"]
        self.artifact = json.loads((directory / "manifest.json").read_text())
        controller = (directory / "controller.json").read_bytes()
        if not (self.artifact["controller_sha256"] == sha
                == hashlib.sha256(controller).hexdigest()
                and json.loads(controller) == disclosure["configuration"]):
            raise SystemExit(f"refused: {group['artifact']} did not write this battle's graphs")
        self.calls = [json.loads(line) for line in (directory / "calls.jsonl").open()]
        self.revisions = []  # (name, manifest, calls) of each revision made from this battle
        suffix = f"/{group['job']}/{group['episode']}"
        for path in sorted((runs / "runs/twwarhammer3").glob("gap-*/*/manifest.json")):
            other = json.loads(path.read_text())
            if not str((other.get("evidence") or {}).get("episode") or "").endswith(suffix):
                continue
            if (other.get("parent") or {}).get("controller_sha256") != sha:
                raise SystemExit(f"refused: {path.parent.name}'s parent is not this battle's")
            self.revisions.append((str(path.parent.relative_to(runs)), other, [
                json.loads(line) for line in (path.parent / "calls.jsonl").open()]))
        if [name for name, _, _ in self.revisions] != group.get("revisions",
                                                                [n for n, _, _ in self.revisions]):
            raise SystemExit(f"refused: revisions found {[n for n, _, _ in self.revisions]}")

    def spec(self, member: str, node: str) -> dict:
        return self.view["graphs"][member]["nodes"][node]

    def step(self, line: int) -> str:
        """One member_event, decision or ack row as a message line."""
        row = self.rows[line]
        record = row.get("record") or {}
        if row.get("kind") == "team" and record.get("event") in ("started", "transition"):
            node, at = record["node"], seconds(record["source"]["time_ms"])
            name = f"{node_label(self.spec(row['member'], node), self.labels)} ({node})"
            if record["event"] == "started":
                return (f"{row['member']}, {at} view: {name} started with "
                        f"{inputs_text(record['inputs'])} (row {line})")
            return (f"{row['member']}, {at} view: {name} -> {record['status']}"
                    + (f", {outcome(record)}" if record.get("outputs") else "")
                    + (f": {record['witness']}" if record.get("witness") else "")
                    + f" (row {line})")
        if row.get("kind") == "decision" and row.get("orders"):
            behavior = row["behavior"]
            node = behavior["node"]
            name = f"{node_label(self.spec(behavior['member'], node), self.labels)} ({node})"
            ack_line = self.acks[row["request"]]
            ack = self.rows[ack_line]["ack"]
            return (f"{behavior['member']}, {seconds(behavior['source_ms'])} view (state seq "
                    f"{behavior['source_seq']}): {name} orders: "
                    f"{orders_text(row['orders'], self.names)}; step status {behavior['status']}"
                    f" (row {line})\nsent as request {row['request'].rsplit('-r', 1)[-1]} at "
                    f"{seconds(row['decision_time_ms'])}; applied at "
                    f"{seconds(ack['applied_ms'])}: " + ", ".join(
                        f"{self.names[r['unit']]} {'ok' if r['ok'] else 'refused'}"
                        for r in ack["results"]) + f" (row {ack_line})")
        raise SystemExit(f"refused: trace row {line} is not a graph step or an order batch")

    def brief(self, line: int) -> str:
        """step()'s short form for a message beside a map: node ids, as the boxes' code lines."""
        row = self.rows[line]
        record = row.get("record") or {}
        if row.get("kind") == "team" and record.get("event") == "started":
            return (f"{seconds(record['source']['time_ms'])}: {record['node']} started, "
                    f"{inputs_text(record['inputs'])} (row {line})")
        if row.get("kind") == "team" and record.get("event") == "transition":
            return (f"{seconds(record['source']['time_ms'])}: {record['node']} -> "
                    f"{record['status']}" + (f", {outcome(record)}" if record.get("outputs")
                                             else "")
                    + (f": {record['witness']}" if record.get("witness") else "")
                    + f" (row {line})")
        if row.get("kind") == "decision" and row.get("orders"):
            ack_line = self.acks[row["request"]]
            ack = self.rows[ack_line]["ack"]
            return (f"{seconds(row['behavior']['source_ms'])} view: {row['behavior']['node']} "
                    f"orders {orders_text(row['orders'], self.names)} (row {line}); sent at "
                    f"{seconds(row['decision_time_ms'])}, applied at {seconds(ack['applied_ms'])}: "
                    + ", ".join(f"{self.names[r['unit']]} {'ok' if r['ok'] else 'refused'}"
                                for r in ack["results"]) + f" (row {ack_line})")
        raise SystemExit(f"refused: trace row {line} is not a graph step or an order batch")

    def viewer(self, line: int) -> str:
        """The member a view (an observation row) went to: the team input row just before it."""
        given = self.rows.get(line - 1) or {}
        if (given.get("event") != "input" or self.rows[line].get("kind") != "observation"
                or given.get("source_seq") != self.rows[line]["observation"]["seq"]):
            raise SystemExit(f"refused: trace row {line} is not a view given to a member")
        return given["member"]

    def map(self, line: int, orders: list, note: str) -> dict:
        return map_frame(trace_frame(self.data, line), self.names, orders, note,
                         f"{self.path} row {line}")

    def authoring(self) -> tuple[list, list, dict]:
        """(blocks before, blocks between, counts) for the side cells and the card."""
        def blocks(calls):
            return [{"label": SHORT_ROLE.get(c["role"], c["role"]),
                     "title": f"{c['role']}: {sum(a['seconds'] for a in c['attempts']):.1f} s "
                              f"wall clock, ${sum(a['usd'] for a in c['attempts']):.4f}"}
                    for c in calls]
        totals = self.artifact["totals"]
        between = [m["totals"] for _, m, _ in self.revisions]
        return blocks(self.calls), [b for _, _, c in self.revisions for b in blocks(c)], {
            "before": totals["calls"], "before_s": round(totals["seconds"]),
            "before_usd": totals["usd"], "between": sum(t["calls"] for t in between),
            "between_s": [round(t["seconds"]) for t in between],
            "between_usd": sum(t["usd"] for t in between)}

    def task_message(self) -> dict:
        tasks = json.loads(self.calls[0]["attempts"][-1]["text"])["tasks"]
        name = Path(self.group["artifact"]).name
        return {"title": f"The task and the coordinator's member tasks ({name})",
                "text": "\n".join([f"task: {self.artifact['task']}"]
                                  + [f"{t['member']}: {t['task']}" for t in tasks]),
                "source": f"{self.group['artifact']}/manifest.json task and calls.jsonl line 1 "
                          "(the coordinator's reply)"}

    def played(self, sha: str) -> list[str]:
        """The recorded battles that played the graphs with this controller sha256."""
        return [f"{job}/{episode}" for job, episode, card in recorded_cards(self.runs)
                if ((card.get("disclosure") or {}).get("artifact") or {}).get(
                    "controller_sha256") == sha]


def model_group(group: dict, recipe: dict, runs: Path, lanes: dict) -> tuple[dict, dict, dict]:
    """A model controller's group: one wait bar per decision, its order marks and its card."""
    start, end = recipe["window"]
    key, story = group["id"], recipe["story"]
    job, episode = runs / group["job"], runs / group["job"] / group["episode"]
    manifest = json.loads((job / "manifest.json").read_text())
    result = json.loads((episode / "result.json").read_text())
    data = replay.build(episode, manifest)
    names = {entry["id"]: label(entry) for entry in data["roster"]}
    path = f"{group['job']}/{group['episode']}/trace.jsonl"
    decisions = data["decisions"]
    kinds, previous = [], None  # rests on JUDGEMENT? Resent rule (EXAMPLES)
    for decision in decisions:
        orders = [o["order"] for o in decision["orders"]]
        kinds.append(None if not orders else "resent" if orders == previous else "new")
        previous = orders or previous
    calls = [0, result["llm"]["calls"], 0]
    # The calls' split, recounted from trace.jsonl: llm.calls counts attempts; an attempt after a
    # refused one is a re-ask; an exchange no decision used must have been still out at the end
    # (only the result row after it; sent before the last ack's wall clock plus the battle time
    # left after it, replied after that).
    rows = [json.loads(line) for line in (episode / "trace.jsonl").open()]
    exchanges = [(n, r) for n, r in enumerate(rows, 1) if r.get("kind") == "model_exchange"]
    reasks = sum(len(r["attempts"]) for _, r in exchanges) - len(exchanges)
    used = {a["exchange_id"] for d in decisions for a in d["attempts"]}
    unused = [(n, r) for n, r in exchanges if not {a["exchange_id"] for a in r["attempts"]} & used]
    ack = next(r for r in reversed(rows) if r.get("kind") == "ack")
    end_s = ack["elapsed"] + (result["battle_ms"] - ack["ack"]["applied_ms"]) / 1000
    if (len(decisions) + reasks + len(unused) != calls[1]
            or any(not a.get("error") for _, r in exchanges for a in r["attempts"][:-1])
            or any([r.get("kind") for r in rows[n:]] != ["result"]
                   or not r["elapsed"] - sum(a["seconds"] for a in r["attempts"]) < end_s
                   < r["elapsed"] for n, r in unused)):
        raise SystemExit(f"refused: {calls[1]} calls are not {len(decisions)} decisions, "
                         f"{reasks} re-asks and {len(unused)} calls out at the end")
    lanes["rows"] += [
        header(group, calls), {"id": f"{key}.model", "label": "model", "who": "model"},
        {"id": f"{key}.orders", "label": "orders"}]
    lanes["cells"] += [{"row": f"{key}.model", "column": column, "blocks": [],
                        "text": group[column]} for column in ("before", "between")]
    marks, replies, unread = {}, [], []
    for i, decision in enumerate(decisions):
        if not start <= decision["time_ms"] < end or decision.get("applied_ms") is None:
            continue
        number, applied = decision["request"].rsplit("-r", 1)[-1], decision["applied_ms"]
        if applied - decision["time_ms"] != decision["latency"]["delay_ms"]:
            raise SystemExit(f"refused: request {number}'s delay is not applied minus view time")
        later = decisions[i + 1]["seq"] - decision["seq"] - 1 if i + 1 < len(decisions) else 0
        cut = applied > end
        lanes["items"].append({
            "row": f"{key}.model", "kind": "wait", "who": "model",
            "label": f"request {number} · view from {seconds(decision['time_ms'])} (state seq "
                     f"{decision['seq']}) · {'applies' if cut else 'applied'} at "
                     f"{seconds(applied)} · {later} newer view{'' if later == 1 else 's'} "
                     "arrived unread",
            "from": decision["time_ms"], "to": min(applied, end),
            "text": f"applies at {seconds(applied)}" if cut
                    else f"{decision['latency']['delay_ms'] / 1000:.1f}"})
        if cut:
            continue
        replies.append(kinds[i])
        unread.append(later)
        if kinds[i]:
            mark = marks.setdefault(kinds[i], {"row": f"{key}.orders", "kind": kinds[i],
                                               "at": [], "titles": []})
            mark["at"].append(applied)
            mark["titles"].append(
                f"request {number} · from the {seconds(decision['time_ms'])} view · applied at "
                f"{seconds(applied)} · " + orders_text([o["order"] for o in decision["orders"]],
                                                       names)
                + (" · the same orders sent again" if kinds[i] == "resent" else ""))
    lanes["marks"] += marks.values()
    delays = result["delays_ms"]
    carried, new = sum(1 for k in kinds if k), kinds.count("new")
    base, card = result["card"]["name"].split("@")[0], result["card"]
    on_main = head_constant(CONTROLLERS, "VERSIONS")[base]
    played = sum(1 for _, _, c in recorded_cards(runs)
                 if str(c.get("name", "")).split("@")[0] == base and c.get("version") == on_main)
    example, number, row = battle_fields(group, recipe["results"], story,
                                         manifest["source_revision"], group["refs"])
    battle_s = seconds(result["battle_ms"])
    cards = {
        "calls": f"{' / '.join(map(str, calls))}: {calls[1]} calls during the battle: "
                 f"{len(decisions)} decisions, {reasks} re-ask{'' if reasks == 1 else 's'} after "
                 f"a refused batch, and {len(unused)} call{'' if len(unused) == 1 else 's'} still "
                 f"out when the battle ended, {'its reply' if len(unused) == 1 else 'replies'} "
                 "unused (result.json llm.calls; split recounted from trace.jsonl); none before "
                 "or between battles",
        "decisions": f"{len(decisions)} decisions from {seconds(result['start_time_ms'])} to the "
                     f"end at {battle_s}; {carried} carried orders, {new} of them new and "
                     f"{carried - new} the same as the previous non-empty batch (recounted from "
                     "trace.jsonl)",
        "view_age": view_age(delays),
        "example": f"{example['job']} · {example['date_text']} · {base} {card['version']} at "
                   f"{example['commit']}, {on_main} on main, "
                   + ("never played" if not played else f"played in {played} battles")
                   + f" · {model_name(card['model'])} {card['effort']} · {row['outcome']} at "
                     f"{battle_s} · one battle (results.csv:{number})"}
    first, second = (next(d for d in decisions if d["request"].endswith("-" + r))
                     for r in group["decisions"])
    later = second["seq"] - first["seq"] - 1
    moves = [{"unit": o["order"]["unit"], "x": o["order"]["x"], "z": o["order"]["z"]}
             for o in first["orders"] if o["order"]["type"] == "move"]
    reply = "Reply {n}: its orders and reason (trace row {row})"
    example["messages"] = {
        "r1": {"title": reply.format(n=group["decisions"][0][1:], row=first["source"]["line"]),
               "text": f"orders: {orders_text([o['order'] for o in first['orders']], names)}"
                       f"\nreason: \"{first['reason']}\"",
               "source": f"{path} row {first['source']['line']}"},
        "r1-applied": {
            "title": f"Request {group['decisions'][0][1:]} applied (trace row "
                     f"{first['ack_source']['line']})",
            "text": f"applied at {seconds(first['applied_ms'])}, from the view of "
                    f"{seconds(first['time_ms'])} (state seq {first['seq']}): "
                    f"{first['latency']['delay_ms'] / 1000:.1f} s old\nresults: "
                    + ", ".join(f"{names[o['order']['unit']]} "
                                f"{'ok' if o['ack']['ok'] else 'refused'}"
                                for o in first["orders"])
                    + f"\n{later} newer view{'' if later == 1 else 's'} arrived unread while the "
                      f"model thought; the next one read was state seq {second['seq']}",
            "source": f"{path} row {first['ack_source']['line']}"},
        "r2": {"title": reply.format(n=group["decisions"][1][1:], row=second["source"]["line"]),
               "text": "orders: " + (orders_text([o["order"] for o in second["orders"]], names)
                                     or "none") + f"\nreason: \"{second['reason']}\"",
               "source": f"{path} row {second['source']['line']}"}}
    example["frames"] = {"r1": map_frame(
        data["frames"][first["basis_frame"]], names, moves,
        f"What the model saw at {seconds(first['time_ms'])}: our units blue, the enemies our side "
        "could see red; dashed: the moves of its first reply. x right, z up.",
        f"{path} row {data['frames'][first['basis_frame']]['source']['line']}")}
    found = {"calls": calls, "decisions": len(decisions), "result_decisions": result["decisions"],
             "reasks": reasks, "unused_calls": len(unused), "carried": carried, "new": new,
             "replies_in_window": len(replies),
             "new_in_window": replies.count("new"), "unread_in_window": unread,
             "first_view_ms": decisions[0]["time_ms"],
             "first_applied_ms": decisions[0]["applied_ms"], "delay_ms": spread(delays),
             "delays_n": len(delays), "on_main": on_main, "on_main_battles": played}
    return example, cards, found


def graph_group(group: dict, recipe: dict, runs: Path, lanes: dict) -> tuple[dict, dict, dict]:
    """A GaP group: model calls in the side cells, one code lane per member, its order marks."""
    start, end = recipe["window"]
    key, story = group["id"], recipe["story"]
    gap = GaP(group, runs)
    before, between, spent = gap.authoring()
    result = gap.result
    during = (result.get("llm") or {}).get("calls", 0) + sum(
        m["calls"] for m in result["members"].values())
    calls = [spent["before"], during, spent["between"]]
    owners = next(r for r in gap.rows.values() if r.get("event") == "partition")["ownership"]
    lanes["rows"] += [
        header(group, calls), {"id": f"{key}.model", "label": "model", "who": "model",
         **({"empty": group["empty"]} if not during else {})},
        *({"id": f"{key}.{member}", "who": who,
           "label": f"{member}: {', '.join(gap.names[u] for u in owners[member])}"}
          for member, who in group["members"].items()),
        {"id": f"{key}.orders", "label": "orders"}]
    artifact, revisions = Path(group["artifact"]).name, [Path(n).name for n, _, _ in gap.revisions]
    lanes["cells"] += [
        {"row": f"{key}.model", "column": "before", "blocks": before,
         "text": f"{spent['before']} calls · about {spent['before_s']} s, wall clock · "
                 f"${spent['before_usd']:.4f}"},
        {"row": f"{key}.model", "column": "between", "blocks": between,
         "text": f"{spent['between']} calls · {', '.join(revisions)} · "
                 f"${spent['between_usd']:.4f}"}]
    ticks = Counter()
    for member, who in group["members"].items():
        started, groups = {}, {}
        for event in gap.view["events"]:
            at = event["source"]["time_ms"]
            if event["member"] != member:
                continue
            if event["kind"] == "started" and start <= at < end:
                started[event["node"], event["node_run"]] = event
            if event["kind"] != "transition" or (event["node"], event["node_run"]) not in started:
                continue
            begun = started.pop((event["node"], event["node_run"]))
            spec = gap.spec(member, event["node"])
            name = node_label(spec, gap.labels)
            if at == begun["source"]["time_ms"]:
                groups.setdefault((event["node"], name, outcome(event)), []).append(at)
                continue
            limit = spec.get("timeout_ms") or head_constant(SKILLS, "TIMEOUT_MS", gap.commit)
            target = begun["inputs"].get("target", "")
            running = at >= end
            lanes["items"].append({
                "row": f"{key}.{member}", "kind": "skill", "who": who,
                "label": f"{name} ({event['node']}): started from the "
                         f"{seconds(begun['source']['time_ms'])} view with "
                         f"{inputs_text(begun['inputs'])}; "
                         + (f"still running at {seconds(end)}, ends {event['status']} at "
                            f"{seconds(at)}" if running else f"{event['status']} at {seconds(at)}"),
                "from": begun["source"]["time_ms"], "to": min(at, end),
                "text": f"{name.split()[0]} {gap.names.get(target, target)}: "
                        + (f"running (gives up after {limit // 1000} s without "
                           f"{WITNESS.get(spec['op'], 'its effect')})" if running
                           else event["status"])})
        if started:
            raise SystemExit(f"refused: {member} steps started in the window never finished")
        for (node, name, result_text), times in groups.items():
            # label: each tick's tooltip; text: the line drawn once over a group, with its count
            lanes["ticks"].append({"row": f"{key}.{member}", "at": times, "who": who,
                                   "label": f"{name}: {result_text}",
                                   **({"text": f"{name}: {result_text} ×{len(times)} here"}
                                      if len(times) > 1 else {})})
            ticks[member] += len(times)
    marks, previous, kinds, window = {}, {}, Counter(), []
    carried = Counter()
    for line, row in gap.rows.items():
        if row.get("kind") != "decision" or not row.get("orders"):
            continue
        member = row["behavior"]["member"]
        carried[member] += 1
        kind = "resent" if previous.get(member) == row["orders"] else "new"  # Resent rule
        previous[member] = row["orders"]
        kinds[kind] += 1
        applied = gap.rows[gap.acks[row["request"]]]["ack"]["applied_ms"]
        if not start <= applied <= end:
            continue
        who = group["members"][member]
        node = row["behavior"]["node"]
        window.append((applied, kind, row["behavior"]["source_ms"], member))
        mark = marks.setdefault((kind, who), {"row": f"{key}.orders", "kind": kind, "who": who,
                                              "at": [], "titles": []})
        mark["at"].append(applied)
        mark["titles"].append(
            f"{member} · {node_label(gap.spec(member, node), gap.labels)} ({node}) · from the "
            f"{seconds(row['behavior']['source_ms'])} view · applied at {seconds(applied)} · "
            + orders_text(row["orders"], gap.names)
            + (" · the same orders sent again" if kind == "resent" else ""))
    lanes["marks"] += marks.values()
    delays = result["delays_ms"]
    example, number, row = battle_fields(group, recipe["results"], story, gap.commit,
                                         group["refs"])
    battle_s, per = seconds(result["battle_ms"]), {m["decisions"] for m in
                                                   result["members"].values()}
    on_main = re.search(r'^VERSION = f"\{ARTIFACT_TYPE\}-(v\d+)"', git_blob("HEAD", AUTHOR)
                        .decode(), re.M)[1]
    cards = {
        "calls": f"{' / '.join(map(str, calls))}: before the battle {artifact}, about "
                 f"{spent['before_s']} s wall clock, ${spent['before_usd']:.4f}; between battles "
                 + "; ".join(f"{name}, about {s} s, ${m['totals']['usd']:.4f}" for name, s, m in
                             zip(revisions, spent["between_s"], (m for _, m, _ in gap.revisions)))
                 + " (manifest.json totals); none during it (result.json members.*.calls)",
        "decisions": f"{result['decisions']} decisions from {seconds(result['start_time_ms'])} "
                     f"to the end at {battle_s}, "
                     + (f"{per.pop()} per member" if len(per) == 1 else ", ".join(
                         f"{m} {v['decisions']}" for m, v in result["members"].items()))
                     + f"; {sum(carried.values())} carried orders ("
                     + ", ".join(f"{carried[m]} {m}" for m in sorted(carried, key=carried.get,
                                                                      reverse=True))
                     + f"), {kinds['new']} of them new and {kinds['resent']} the same as that "
                       "member's previous non-empty batch (recounted from trace.jsonl)",
        "view_age": view_age(delays),
        "example": f"{example['job']} · {example['date_text']} · graphs {artifact} (author "
                   f"{gap.artifact['version'].rsplit('-', 1)[-1]}) at {example['commit']}, author "
                   f"{on_main} on main · graphs by {model_name(gap.artifact['model'])} "
                   f"{gap.artifact['effort']} · {row['outcome']} at {battle_s} · one battle "
                   f"(results.csv:{number})"}
    steps, order, view = (group["rows"][k] for k in ("steps", "order", "view"))
    target = gap.rows[order]["orders"][0]
    old = gap.result["card"]["disclosure"]["configuration"]["members"]
    changes, changed = [], []
    for name, other, _ in gap.revisions:
        new_members = json.loads((runs / name / "controller.json").read_text())["members"]
        for member in group["members"]:
            a, b = (m[member]["controller"]["graph"]["nodes"] for m in (old, new_members))
            added = [n for n in b if n not in a]
            edited = sorted(n for n in a if n in b and a[n] != b[n])
            if not (added or edited or [n for n in a if n not in b]):
                changes.append(f"{member}'s graph: unchanged")
                continue
            changed.append(member)
            changes.append(f"{member}'s graph: " + "; ".join(
                f"added {n} ({node_label(b[n], gap.labels)}), after "
                f"{', '.join(p for p in b if n in b[p]['next'].values())}, before "
                f"{b[n]['next'].get('succeeded')}" for n in added)
                + (f"; also changed {', '.join(edited)}" if edited else "")
                + (f"; removed {', '.join(n for n in a if n not in b)}"
                   if [n for n in a if n not in b] else ""))
    revised = [(name, other, gap.played(other["controller_sha256"]))
               for name, other, _ in gap.revisions]
    lines = []
    for name, other, battles in revised:
        counts = other["evidence"]["counts"]
        lines.append(f"{Path(name).name} read this battle's public record: " + "; ".join(
            f"{m} {c['views']} views, {c['orders']} orders" for m, c in counts.items())
            + " (manifest.json evidence.counts)")
        for battle in battles:
            job_name, episode_name = battle.split("/")
            played_line, played_row = results_line(recipe["results"], job_name, episode_name)
            played_result = json.loads((runs / "runs/twwarhammer3/battle" / battle /
                                        "result.json").read_text())
            lines.append(f"these graphs then played {job_name}: {played_row['outcome']} at "
                         f"{seconds(played_result['battle_ms'])}, one battle (results.csv line "
                         f"{played_line})")
    example["messages"] = {
        "task": gap.task_message(),
        "steps": {"title": "Two step records (trace rows "
                           + " and ".join(map(str, steps)) + ")",
                  "text": "\n".join(gap.step(n) for n in steps),
                  "source": f"{gap.path} rows " + ", ".join(map(str, steps))},
        "order": {"title": f"The line's first order and its acknowledgement (trace rows {order} "
                           f"and {gap.acks[gap.rows[order]['request']]})",
                  "text": gap.step(order),
                  "source": f"{gap.path} rows {order} and {gap.acks[gap.rows[order]['request']]}"},
        "revision": {"title": "Between battles: the revision made from this battle's record",
                     "text": "\n".join(lines[:1] + changes
                                       + lines[1:]),
                     "source": ", ".join(f"{n}/manifest.json and controller.json"
                                         for n, _, _ in gap.revisions)}}
    frame = trace_frame(gap.data, view)
    example["frames"] = {"attack": gap.map(
        view, [aim(frame, target["unit"], target["target"])],
        f"The units at {seconds(frame['time_ms'])}, the view the line's attack came from: ours "
        "blue, the enemies our side could see red; dashed: the attack. x right, z up.")}
    first = window[0]
    resends = [b[0] - a[0] for a, b in zip(window, window[1:]) if a[3] == b[3]]
    found = {"calls": calls, "trace_model_exchanges": sum(
        1 for r in gap.rows.values() if r.get("kind") == "model_exchange"),
        "decisions": result["decisions"], "member_decisions": {
            m: v["decisions"] for m, v in result["members"].items()},
        "carried": sum(carried.values()), "carried_by_member": dict(carried),
        "new": kinds["new"], "resent_in_window": sum(1 for w in window if w[1] == "resent"),
        "new_in_window": sum(1 for w in window if w[1] == "new"),
        "first_view_ms": first[2], "first_applied_ms": first[0],
        "resend_every_ms": statistics.median(resends),
        "resend_range_ms": [min(resends), max(resends)], "author_s": spent["before_s"],
        "between_s": spent["between_s"], "changed_members": changed,
        **{f"{member}_ticks": n for member, n in ticks.items()},
        "delay_ms": spread(delays), "delays_n": len(delays), "author_on_main": on_main,
        "revised_battles": [b for _, _, bs in revised for b in bs],
        "revision_orders_match": all(c["orders"] == carried[m] for _, other, _ in gap.revisions
                                     for m, c in other["evidence"]["counts"].items())}
    return example, cards, found


def build_methods(recipe: dict, runs: Path) -> dict:
    """The 'Control methods' lanes: one group per method on one battle window, from one recorded
    battle each, and each group's card numbers."""
    lanes = {"columns": True, "rows": [], "items": [], "ticks": [], "marks": [], "cells": []}
    examples, cards = {}, {}
    for group in recipe["groups"]:
        make = model_group if group["kind"] == "model" else graph_group
        example, cards[group["id"]], found = make(group, recipe, runs, lanes)
        examples[group["example"]] = example
        check_counts(f"methods {group['id']}", group["stated"], found)
    return {"methods": {"story": recipe["story"], "examples": list(examples),
                        "window": recipe["window"], "lanes": lanes, "cards": cards}, **examples}


def build_graph(recipe: dict, runs: Path) -> dict:
    """The recorded graphs as boxes and wires (only steps that ran and exits taken, one row per
    member in graph-view's order and labels) and the graph story's messages and maps."""
    gap = GaP(recipe, runs)
    rows, lay = recipe["rows"], recipe["layout"]
    transitions = [e for e in gap.view["events"] if e["kind"] == "transition"]
    ran = Counter((e["member"], e["node"]) for e in gap.view["events"] if e["kind"] == "started")
    taken = Counter((e["member"], e["node"], e["status"]) for e in transitions)
    elements, wires, unran, untaken = [], [], [], []

    def status(step):  # a box's status, and its exits'
        return recipe["status"]["live" if step["op"] in recipe["status"]["live_ops"] else "offline"]
    for row_number, member in enumerate(recipe["members"]):
        spec = gap.view["graphs"][member]
        order = graph_order(spec)
        shown = [n for n in order if ran[member, n]]
        unran += [(member, n) for n in order if not ran[member, n]]
        for i, node in enumerate(shown):
            step = spec["nodes"][node]
            limit = (step.get("timeout_ms") or head_constant(SKILLS, "TIMEOUT_MS", gap.commit)
                     if step["op"] in gap.labels[2] else None)
            note = ([f"{step['op']} with mode {step['mode']}."] if step.get("mode") else []) + (
                [f"Time limit {limit // 1000} s: the step fails if the game shows no "
                 f"{WITNESS.get(step['op'], 'effect')} by then."] if limit else [])
            elements.append({
                "id": f"{member}.{node}", "label": node_label(step, gap.labels),
                "code": f"{node} · {step['op']}", **({"note": " ".join(note)} if note else {}),
                "kind": "process", "where": "WSL Python",
                "x": lay["x"] + i * lay["step"], "y": lay["y"][row_number],
                "w": lay["w"], "h": lay["h"], "status": status(step),
                "refs": [LABEL_REF] + ([LIMIT_REF, DEADLINE_REF] if limit else [])})
        for node in order:
            step = spec["nodes"][node]
            exits: dict = {}
            for name in exit_order(step):
                if not taken[member, node, name] or node not in shown:
                    untaken.append((member, node, name))
                    continue
                exits.setdefault(step["next"][name], []).append(
                    f"{name} ×{taken[member, node, name]}")
            for successor, parts in exits.items():
                if successor not in shown:
                    raise SystemExit(f"refused: {member}.{node} exits to {successor}, which "
                                     "never ran")
                a, b = shown.index(node), shown.index(successor)
                wire = {"id": f"{member}.{node}>{successor}", "from": f"{member}.{node}",
                        "to": f"{member}.{successor}", "label": " / ".join(parts),
                        "status": status(step), "refs": [STEP_REF]}
                if b == a + 1:  # to the next box: an arc above the row
                    wire["bend"] = lay["arc"]
                elif b != a:  # back or skipping: below the row, deeper the more boxes it skips
                    wire["bend"] = lay["bend"] * abs(b - a) * (1 if b > a else -1)
                wires.append(wire)
    if len(elements) > 12:
        raise SystemExit(f"refused: {len(elements)} boxes, over 12; use twwarhammer3 graph-view")
    exits_by_name = Counter(name for _, _, name in untaken)
    hidden = {"steps": [{"id": f"{m}.{n}", "label": node_label(gap.spec(m, n), gap.labels)}
                        for m, n in unran],
              "exits": [f"{m}.{n} {name} > {m}.{gap.spec(m, n)['next'][name]}"
                        for m, n, name in untaken],
              "text": "Hidden: " + "; ".join(
                  f"the {m}'s {node_label(gap.spec(m, n), gap.labels)} step ({n}), which never "
                  "ran" for m, n in unran)
              + f"; and {len(untaken)} exits never taken in this battle ("
              + ", ".join(f"{count} {name}" for name, count in exits_by_name.most_common())
              + "). graph-view draws the whole graph."}
    _, _, spent = gap.authoring()
    contact = next(e for e in transitions if e["member"] == "cavalry" and e["status"] == "yes")
    contact_ms = contact["source"]["time_ms"]
    nos = [e for e in transitions if e["member"] == "cavalry" and e["status"] == "no"
           and e["source"]["time_ms"] < contact_ms]
    deadlines = [e for e in transitions if e["member"] == "line" and e["status"] == "failed"
                 and e["witness"] == "deadline without effect witness"
                 and e["source"]["time_ms"] < contact_ms]
    line_rows, charge_rows = rows["line"], rows["charge"]
    order = gap.rows[rows["order"]]
    charge = gap.rows[charge_rows[-1]]
    witness = gap.rows[rows["witness"]]["record"]
    frames = {key: trace_frame(gap.data, rows[key]) for key in
              ("start", "view", "walk", "deadline_view", "melee_view", "charge_view",
               "witness_view")}
    line_unit, line_target = order["orders"][0]["unit"], order["orders"][0]["target"]
    cav_unit, cav_target = charge["orders"][0]["unit"], charge["orders"][0]["target"]
    seq = {r["observation"]["seq"]: n for n, r in gap.rows.items()
           if r.get("kind") == "observation"}
    judged = seq[gap.rows[rows["melee"]]["record"]["source"]["seq"]]  # the view engage read
    walk_seq = gap.rows[rows["walk"]]["observation"]["seq"]
    if (gap.viewer(rows["walk"]), gap.viewer(rows["melee_view"]), gap.viewer(judged)) != (
            "cavalry", "cavalry", "line") or not any(
            e["member"] == "cavalry" and e["source"]["seq"] == walk_seq for e in transitions):
        raise SystemExit("refused: the walk or melee map is not a cavalry view its graph read, or "
                         "engage was not judged from a line view")
    others = sorted((u["id"] for u in frames["witness_view"]["enemy"] if u["id"] != cav_target),
                    key=lambda uid: apart(frames["witness_view"], cav_unit, uid))
    path = gap.path
    near = others[0]
    note = "ours blue, the enemies our side could see red"
    story_exists = (ROOT / recipe["story"]).exists()
    refs = (story_refs(recipe["story"]) if story_exists else recipe["refs"]) + [ORDER_REF] + [
        ref for item in elements + wires for ref in item["refs"]]
    example, number, row = battle_fields(recipe, recipe["results"], recipe["story"],
                                         gap.commit, refs)
    print(f"  graph: cited files from {'the story' if story_exists else 'the recipe refs'} "
          f"({recipe['story']} {'exists' if story_exists else 'does not exist yet'}) and the "
          "generated boxes and wires")
    example["graph"] = {"elements": elements, "wires": wires, "hidden": hidden,
                        "refs": [ORDER_REF]}  # the order of each row's boxes
    # Each message sits above a map in the side panel: lines() keeps it to 9 short lines.
    tasks = json.loads(gap.calls[0]["attempts"][-1]["text"])["tasks"]
    walk_enemies: dict = {}
    for unit in frames["walk"]["enemy"]:  # enemies by state: the map shows where they are
        state = ", ".join(unit.get("state") or []) or "idle"
        walk_enemies.setdefault(state, []).append(unit["id"])
    attack_ack = gap.acks[order["request"]]
    example["messages"] = {
        "author": {"title": f"Before the battle: {spent['before']} calls "
                            f"({Path(recipe['artifact']).name}); the coordinator wrote the "
                            "member tasks",
                   "text": lines(", ".join(
                                     f"{c['role']} {sum(a['seconds'] for a in c['attempts']):.1f} s"
                                     for c in gap.calls),
                                 f"about {spent['before_s']} s wall clock in all, "
                                 f"${spent['before_usd']:.4f}",
                                 *(f"{t['member']}'s task: \"{clip(t['task'], 100)}\""
                                   for t in tasks)),
                   "source": f"{recipe['artifact']}/calls.jsonl (line 1: the coordinator's reply) "
                             "and manifest.json totals"},
        "line": {"title": "The line's first steps (trace rows "
                          + ", ".join(map(str, line_rows)) + ")",
                 "text": lines(*(gap.brief(n) for n in line_rows)),
                 "source": f"{path} rows " + ", ".join(map(str, line_rows))},
        "accepted": {"title": f"Accepted is not done (trace rows {rows['order']} and "
                              f"{attack_ack})",
                     "text": lines(gap.brief(rows["order"]),
                                   f"step status still {order['behavior']['status']}"),
                     "source": f"{path} rows {rows['order']} and {attack_ack}"},
        "contact": {"title": f"The cavalry's contact step (trace rows {rows['contact']}, "
                             f"{contact['line']} and {rows['walk']})",
                    "text": lines(gap.brief(rows["contact"]),
                                  f"no {len(nos)} times, {seconds(nos[0]['source']['time_ms'])} "
                                  f"to {seconds(nos[-1]['source']['time_ms'])}; first yes from "
                                  f"the {seconds(contact_ms)} view (row {contact['line']})",
                                  f"the cavalry's {seconds(frames['walk']['time_ms'])} view "
                                  f"(row {rows['walk']}), x, z:",
                                  *(spot(frames["walk"], u["id"], gap.names)
                                    for u in frames["walk"]["friendly"]),
                                  *(f"{', '.join(ids)}: {state}"
                                    for state, ids in walk_enemies.items())),
                    "source": f"{path} rows {rows['contact']}, {contact['line']} and "
                              f"{rows['walk']}"},
        "deadlines": {"title": "Engage gives up without melee (trace rows "
                               + ", ".join(str(e["line"]) for e in deadlines)
                               + f" and {rows['deadline_view']})",
                      "text": lines(f"{', '.join(sorted({e['node'] for e in deadlines}))} -> "
                                    f"failed: {deadlines[0]['witness']}",
                                    f"{len(deadlines)} times before contact, in the views of",
                                    *(", ".join(f"{seconds(e['source']['time_ms'])} (row "
                                                f"{e['line']})" for e in deadlines[i:i + 2])
                                      for i in range(0, len(deadlines), 2)),
                                    f"{seconds(frames['deadline_view']['time_ms'])} view (row "
                                    f"{rows['deadline_view']}), x, z:",
                                    spot(frames["deadline_view"], line_unit, gap.names)),
                      "source": f"{path} rows " + ", ".join(str(e["line"]) for e in deadlines)
                                + f" and {rows['deadline_view']}"},
        "melee": {"title": f"Engage done (trace rows {rows['melee_view']}, {judged} and "
                            f"{rows['melee']})",
                  "text": lines(f"the cavalry's {seconds(frames['melee_view']['time_ms'])} view "
                                f"(row {rows['melee_view']}), x, z:",
                                spot(frames["melee_view"], line_unit, gap.names),
                                spot(frames["melee_view"], line_target, gap.names),
                                f"{line_unit} and {line_target} "
                                f"{apart(frames['melee_view'], line_unit, line_target)} m apart",
                                f"from the line's view (row {judged}): {gap.brief(rows['melee'])}"),
                  "source": f"{path} rows {rows['melee_view']}, {judged} and {rows['melee']}"},
        "charge": {"title": "The cavalry's charge (trace rows "
                            + ", ".join(map(str, charge_rows))
                            + f" and {gap.acks[charge['request']]})",
                   "text": lines(*(gap.brief(n) for n in charge_rows),
                                 f"{cav_unit} {apart(frames['charge_view'], cav_unit, cav_target)}"
                                 f" m from {cav_target} in the "
                                 f"{seconds(frames['charge_view']['time_ms'])} view"),
                   "source": f"{path} rows " + ", ".join(map(str, charge_rows))
                             + f", {gap.acks[charge['request']]} and {rows['charge_view']}"},
        "witness": {"title": f"The charge counts as done (trace rows {rows['witness_view']} and "
                             f"{rows['witness']})",
                    "text": lines(gap.brief(rows["witness"]),
                                  f"{seconds(frames['witness_view']['time_ms'])} view (row "
                                  f"{rows['witness_view']}), x, z:",
                                  *(spot(frames["witness_view"], u, gap.names)
                                    for u in (cav_unit, cav_target, near)),
                                  f"{cav_unit} to {cav_target} "
                                  f"{apart(frames['witness_view'], cav_unit, cav_target)} m, to "
                                  f"{near} {apart(frames['witness_view'], cav_unit, near)} m "
                                  "(unit centres)",
                                  "the check reads only target and melee state"),
                    "source": f"{path} rows {rows['witness_view']} and {rows['witness']}; "
                              f"{SKILLS}:119-122"}}
    example["frames"] = {
        "start": gap.map(rows["start"], [], f"The units at "
                         f"{seconds(frames['start']['time_ms'])}, the first view both graphs "
                         f"read: {note}. x right, z up."),
        "attack": gap.map(rows["view"], [aim(frames["view"], line_unit, line_target)],
                          f"The units at {seconds(frames['view']['time_ms'])}, the view the "
                          f"line's attack came from: {note}; dashed: the attack. x right, z up."),
        "walk": gap.map(rows["walk"], [], f"The units at {seconds(frames['walk']['time_ms'])}, "
                                          f"a view the cavalry's graph read: {note}. x right, "
                                          "z up."),
        "deadline": gap.map(rows["deadline_view"], [], f"The units at "
                            f"{seconds(frames['deadline_view']['time_ms'])}, when engage gave up "
                            f"the first time: {note}. x right, z up."),
        "melee": gap.map(rows["melee_view"], [], f"The units at "
                         f"{seconds(frames['melee_view']['time_ms'])}, first melee, in the "
                         "cavalry's view; the line judged engage done from its "
                         f"{seconds(gap.rows[judged]['observation']['time_ms'])} view (row "
                         f"{judged}): {note}. x right, z up."),
        "charge": gap.map(rows["charge_view"], [aim(frames["charge_view"], cav_unit, cav_target)],
                          f"The units at {seconds(frames['charge_view']['time_ms'])}, the view "
                          f"the charge came from: {note}; dashed: the charge. x right, z up."),
        "witness": gap.map(rows["witness_view"], [], f"The units at "
                           f"{seconds(frames['witness_view']['time_ms'])}, when the charge "
                           f"counted as done: {note}. x right, z up.")}
    line_first = next(e for e in transitions if e["member"] == "line")
    found = {"calls": spent["before"], "author_s": spent["before_s"],
             "before_usd": round(spent["before_usd"], 4), "battle_ms": gap.result["battle_ms"],
             "outcome": row["outcome"], "boxes": len(elements),
             "hidden_exits": len(untaken), "hidden_steps": [f"{m}.{n}" for m, n in unran],
             "hidden_by_status": dict(exits_by_name),
             "hidden_unran_exits": {f"{m}.{n}": [name for mm, nn, name in untaken
                                                 if (mm, nn) == (m, n)] for m, n in unran},
             "line_first_ms": line_first["source"]["time_ms"], "line_target": line_target,
             "applied_ms": gap.rows[gap.acks[order["request"]]]["ack"]["applied_ms"],
             "no_before_contact": len(nos), "contact_ms": contact_ms,
             "timeout_s": head_constant(SKILLS, "TIMEOUT_MS", gap.commit) // 1000,
             "deadlines_before_contact": len(deadlines),
             "deadline_ms": [e["source"]["time_ms"] for e in deadlines],
             "charge_order_ms": charge["decision_time_ms"],
             "witness_ms": witness["source"]["time_ms"],
             "witness_distance_m": apart(frames["witness_view"], cav_unit, cav_target),
             "witness_nearest": [near, apart(frames["witness_view"], cav_unit, near)],
             "melee_distance_m": apart(frames["melee_view"], line_unit, line_target),
             "charge_distance_m": apart(frames["charge_view"], cav_unit, cav_target),
             "exits": {w["id"]: w["label"] for w in wires}}
    check_counts("graph", recipe["stated"], found)
    return example


def build(recipe: dict, runs: Path) -> dict:
    if recipe.get("kind") == "methods":
        return build_methods(recipe, runs)
    if recipe.get("kind") == "graph":
        return build_graph(recipe, runs)
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
    built = build(EXAMPLES[args.example], args.runs or main_checkout())
    examples = built if EXAMPLES[args.example].get("kind") == "methods" else {args.example: built}
    text = (f'"use strict";\n// Generated by scripts/diagram_examples.py {args.example}; do not '
            f"edit by hand.\nObject.assign(DIAGRAM_EXAMPLES, "
            f"{json.dumps(examples, indent=1, ensure_ascii=False)});\n")
    leak = PRIVATE.search(text)
    if leak:
        raise SystemExit(f"refused: the output matches a private pattern near {leak.start()}")
    out = ROOT / "docs" / f"how-code-works-example-{args.example}.js"
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}: {len(text.encode())} bytes; " + "; ".join(
        f"{name}: {len(example['changed_since'])} of {len(example['files'])} cited files changed "
        f"since {example['commit']}" for name, example in examples.items() if "files" in example))


if __name__ == "__main__":
    main()
