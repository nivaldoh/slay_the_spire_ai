"""Turn one recorded team episode into a measured flow for docs/multi-agent.html.

Step 6 of the diagram plan (runs/multi-agent-diagram-20261031/plan.md, local): instead of a
hand-written walkthrough, the steps and lanes come from the episode's trace.jsonl. The output is
a classic script that the page loads after its data block; it adds one flow to the Team tab, in
the hand-written flows' step format, labelled "measured".

Usage:
    uv run --locked python scripts/diagram_replay.py <episode dir> --revision REV
        [--from-ms A] [--to-ms B] [--out docs/multi-agent-replay.js] [--perfetto FILE]

Times. Battle times are copied: an observation's time_ms, a member view's source_ms, an ack's
applied_ms. WSL wall times (a team event's delivered, started and completed, and a trace row's
elapsed, all from time.time()) are mapped to battle ms by a least-squares line through the
window's input events (delivered, source_ms), as the lanes.py prototype
(runs/twwarhammer3/team-structures-20261021/visualization/lanes.py) does, but fitted on the window
only, because WSL's clock steps. A row's elapsed becomes time.time() by adding the median of
(delivered - elapsed) over the window's input rows. A mapped time is never drawn before the
battle time it follows, and a span shorter than 20 ms is drawn 20 ms long.

--perfetto also writes the lanes as Chrome trace-event JSON, for a cross-check in another viewer
(https://ui.perfetto.dev opens it locally in the browser).
"""
import argparse
import json
import statistics
from pathlib import Path

MIN_MS = 20
OBSERVE = ["team.game>obs", "team.obs>play"]
REQUEST = ["team.team>play", "team.play>orders", "team.orders>game"]


def orders(n):
    return f"{n} order" if n == 1 else f"{n} orders"


def fit(points):
    xs, ys = zip(*points)
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    slope = sum((x - mx) * (y - my) for x, y in points) / sum((x - mx) ** 2 for x in xs)
    worst = max(abs(y - (my + slope * (x - mx))) for x, y in points)
    return (lambda t: my + slope * (t - mx)), slope, worst


def replay(episode: Path, revision: str, start: int, end: int):
    rows = [json.loads(line) for line in (episode / "trace.jsonl").open()]
    name = episode.as_posix()
    name = name[name.index("runs/"):] if "runs/" in name else name  # evidence is cited by runs/
    trace = f"{name}/trace.jsonl"
    inputs = [r for r in rows if r.get("event") == "input" and start <= r["source_ms"] < end]
    if len(inputs) < 2:
        raise SystemExit("fewer than two team input events in the window: nothing to fit")
    battle, slope, worst = fit([(r["delivered"], r["source_ms"]) for r in inputs])
    offsets = [r["delivered"] - r["elapsed"] for r in inputs]
    offset = statistics.median(offsets)
    names = sorted({r["member"] for r in inputs}, key=lambda name: name != "cavalry")
    who = {name: "AB"[i] for i, name in enumerate(names[:2])}
    ack = {r["request"]: (i, r["ack"]) for i, r in enumerate(rows, 1) if r.get("kind") == "ack"}
    sent = {}  # member decision -> battle time of the decision row that carried it
    steps, items, applied_marks = [], [], []
    read = None

    def at(elapsed):
        return battle(elapsed + offset)

    def step(begin, until, caption, refs, **fields):
        begin, until = max(start, begin), min(end, max(until, begin + MIN_MS))
        if begin < until:
            steps.append({"at": round(begin), "until": round(until), **fields,
                          "caption": caption, "refs": refs})

    request = 0
    for i, r in enumerate(rows, 1):
        kind, event = r.get("kind"), r.get("event")
        ref = [f"{trace} row {i}"]
        if kind == "observation" and start <= r["decision_time_ms"] < end:
            t = r["decision_time_ms"]
            read = max(t + MIN_MS, at(r["elapsed"]))
            step(t, read, f"The observation at {t / 1000:.2f} s reaches the play loop.", ref,
                 dots=[OBSERVE])
        elif kind == "decision":
            request += 1
            t, member = r["time_ms"], r["behavior"].get("member")
            if not start <= t < end:
                continue
            j, a = ack.get(r["request"], (None, {}))
            decided = max(read or t, at(r["elapsed"]))
            what = (f"{r['behavior']['decision']}'s batch ({orders(len(r['orders']))})" if member
                    else "an idle poll (no member's batch)")
            step(read or t, decided, f"decide returns {what}.", ref, dots=[["team.play>team"]])
            if a.get("applied_ms") is not None:
                step(decided, a["applied_ms"],
                     f"Request r{request} is applied at {a['applied_ms'] / 1000:.2f} s.",
                     ref + [f"{trace} row {j}"], dots=[REQUEST],
                     **({"who": who[member]} if member else {}))
                items.append({"row": "play", "label": f"r{request}", "from": t,
                              "to": a["applied_ms"], **({"who": who[member]} if member else {})})
                applied_marks.append(a["applied_ms"])
            if member:
                sent[r["behavior"]["decision"]] = (t, a.get("applied_ms"))
        elif kind == "team" and event in ("input", "completed", "feedback") and r["member"] in who:
            w, box = who[r["member"]], f"team.{who[r['member']]}"
            if event == "input" and start <= r["source_ms"] < end:
                m = max(r["source_ms"], battle(r["delivered"]))
                step(m, m, f"{r['decision']} starts on its own view of"
                     f" {r['source_ms'] / 1000:.2f} s.", ref,
                     dots=[["team.team>pool", f"team.pool>{w}"]], who=w)
            elif event == "completed":
                begin, done = battle(r["started"]), battle(r["completed"])
                if r["completed"] - r["started"] > 0.1:
                    step(begin, done, f"{r['decision']} thinks for"
                         f" {r['completed'] - r['started']:.2f} s of WSL time.", ref,
                         box=box, who=w)
                step(done, done, f"{r['decision']} returns {orders(len(r['orders']))}.", ref,
                     dots=[[f"team.{w}>pool"]], who=w)
                collected = max(done, at(r["elapsed"]))
                step(collected, collected, f"decide collects {r['decision']}.", ref,
                     dots=[["team.pool>team"]], who=w)
            elif event == "feedback":
                m = at(r["elapsed"])
                age = r["latency"].get("delay_ms")
                step(m, m, f"{r['decision']} gets its ack"
                     + (f": order age {age} ms." if age else "."), ref,
                     dots=[[f"team.team>{w}"]], who=w)
    sources = {r["decision"]: r["source_ms"] for r in rows if r.get("event") == "input"}
    for r in rows:
        if r.get("event") == "completed" and r["member"] in who:
            source = sources[r["decision"]]
            if not start <= source < end:
                continue
            carried, applied = sent.get(r["decision"], (None, None))
            items.append({"row": who[r["member"]], "label": r["decision"], "input": source,
                          "completed": round(max(source, battle(r["completed"]))),
                          "sent": carried, "applied": applied})
    steps.sort(key=lambda s: s["at"])
    flow = {
        "id": "measured",
        "title": f"Measured replay: {episode.parent.name}",
        "variant": "scripted",
        "clock": "battle time",
        "timing": "measured: one recorded episode",
        "source": f"{name} (recorded at {revision}); generated by"
                  " scripts/diagram_replay.py",
        "drawn": (f"Every step comes from a trace row. WSL times are mapped to battle time by a"
                  f" straight-line fit over this window's {len(inputs)} input events ({slope:.0f}"
                  f" battle ms per WSL second, largest miss {worst:.0f} ms); a row's elapsed is"
                  f" shifted by the median delivered-minus-elapsed ({1000 * offset % 1000:.0f} ms"
                  f" past the second, spread {1000 * (max(offsets) - min(offsets)):.0f} ms). Spans"
                  f" under {MIN_MS} ms are drawn {MIN_MS} ms long."),
        "start": start,
        "end": end,
        "speed": 0.25,
        "steps": steps,
        "lanes": {
            "rows": [{"id": "game", "label": "game: applied"},
                     {"id": "play", "label": "play loop: requests"},
                     *({"id": w, "label": f"member {name}"} for name, w in who.items())],
            "items": items,
            "marks": [{"row": "game", "kind": "applied", "at": applied_marks}],
        },
    }
    return flow


def perfetto(flow):
    """Chrome trace-event JSON: one thread per lane row, complete events in microseconds."""
    rows = {row["id"]: i for i, row in enumerate(flow["lanes"]["rows"], 1)}
    events = [{"ph": "M", "name": "thread_name", "pid": 1, "tid": tid,
               "args": {"name": row["label"]}}
              for row, tid in zip(flow["lanes"]["rows"], rows.values())]

    def span(row, name, begin, until):
        if begin is not None and until is not None and until > begin:
            events.append({"ph": "X", "name": name, "pid": 1, "tid": rows[row],
                           "ts": begin * 1000, "dur": (until - begin) * 1000})

    for item in flow["lanes"]["items"]:
        if "input" not in item:
            span(item["row"], item["label"], item["from"], item["to"])
            continue
        span(item["row"], f"{item['label']} think", item["input"], item["completed"])
        span(item["row"], f"{item['label']} wait", item["completed"], item["sent"])
        span(item["row"], f"{item['label']} engine", item["sent"], item["applied"])
    for t in flow["lanes"]["marks"][0]["at"]:
        events.append({"ph": "i", "s": "t", "name": "applied", "pid": 1, "tid": rows["game"],
                       "ts": t * 1000})
    return {"traceEvents": events, "displayTimeUnit": "ms"}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("episode", type=Path)
    parser.add_argument("--revision", required=True, help="the commit the episode ran at")
    parser.add_argument("--from-ms", type=int, default=5300)
    parser.add_argument("--to-ms", type=int, default=10400)
    parser.add_argument("--out", type=Path, default=Path("docs/multi-agent-replay.js"))
    parser.add_argument("--perfetto", type=Path)
    args = parser.parse_args()
    flow = replay(args.episode, args.revision, args.from_ms, args.to_ms)
    args.out.write_text(
        '"use strict";\n// Generated by scripts/diagram_replay.py; do not edit by hand.\n'
        'DIAGRAM.tabs.find((tab) => tab.id === "team").flows.push(\n'
        + json.dumps(flow, indent=1) + "\n);\n")
    print(f"wrote {args.out}: {len(flow['steps'])} steps, {len(flow['lanes']['items'])} lane items")
    if args.perfetto:
        args.perfetto.write_text(json.dumps(perfetto(flow)))
        print(f"wrote {args.perfetto}")


if __name__ == "__main__":
    main()
