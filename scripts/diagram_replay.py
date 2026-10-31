"""Turn one recorded team episode into a measured flow for docs/multi-agent.html.

Step 6 of the diagram plan (runs/multi-agent-diagram-20261031/plan.md, local): instead of a
hand-written walkthrough, the steps and lanes come from the episode's trace.jsonl. The output is
a classic script that the page loads after its data block; it adds one flow to the Team tab, in
the hand-written flows' step format, labelled "measured".

Usage:
    uv run --locked python scripts/diagram_replay.py <episode dir> --revision REV
        [--from-ms A] [--to-ms B] [--out docs/multi-agent-replay.js] [--perfetto FILE]

Rounds. play.py writes one round's rows in this order: the ack of the previous request, the
team's feedback, the input and completed events of the decide, the observation the decide was
based on, then the decision (play.py:637-718). So each decision row closes a round: the team
events before it ran in that round's decide, and the round starts at the observation's time_ms.
A round belongs to the window when that time is in [A, B).

Times. Battle times are copied: an observation's time_ms, a member view's source_ms, an ack's
applied_ms. The rest are WSL wall times (time.time()), placed on battle time two ways:
- a member call's think span starts at its view's source_ms and lasts its WSL duration
  (completed - delivered) scaled by the fitted rate, so an instant call stays at its view time;
- a decide ends at its trace row's elapsed, mapped by a least-squares line through the window's
  input events (delivered, source_ms), as the lanes.py prototype
  (runs/twwarhammer3/team-structures-20261021/visualization/lanes.py) does, but fitted on the
  window only, because WSL's clock steps; elapsed becomes time.time() by adding the median of
  (delivered - elapsed) over the window's input rows.
No step is drawn before the battle time it follows (its round's observation, or its call's
start), and a span shorter than 20 ms is drawn 20 ms long.

--perfetto also writes the lanes as Chrome trace-event JSON, to view them in another viewer
(https://ui.perfetto.dev opens it locally in the browser). It is built from the flow, so it
checks the drawing, not how the trace was read.
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
    inputs = {r["decision"]: r for r in rows if r.get("event") == "input"}
    window = [r for r in inputs.values() if start <= r["source_ms"] < end]
    if len(window) < 2:
        raise SystemExit("fewer than two team input events in the window: nothing to fit")
    battle, slope, worst = fit([(r["delivered"], r["source_ms"]) for r in window])
    offsets = [r["delivered"] - r["elapsed"] for r in window]
    offset = statistics.median(offsets)
    names = sorted({r["member"] for r in inputs.values()}, key=lambda member: member != "cavalry")
    who = {member: "AB"[i] for i, member in enumerate(names[:2])}
    done = {r["decision"]: (i, r) for i, r in enumerate(rows, 1) if r.get("event") == "completed"}
    acks = {r["request"]: (i, r["ack"]) for i, r in enumerate(rows, 1) if r.get("kind") == "ack"}
    carried = {}  # member decision -> (battle time of the request that carried it, applied_ms)
    for r in rows:
        if r.get("kind") == "decision" and r["behavior"].get("member"):
            applied = acks.get(r["request"], (None, {}))[1].get("applied_ms")
            carried[r["behavior"]["decision"]] = (r["time_ms"], applied)

    def scaled(call, wall):  # a worker time: the call's view time plus its WSL duration
        return call["source_ms"] + (wall - call["delivered"]) * slope

    steps, items, applied_marks = [], [], []

    def step(begin, until, caption, refs, **fields):
        begin, until = max(start, begin), min(end, max(until, begin + MIN_MS))
        if begin < until:
            steps.append({"at": round(begin), "until": round(until), **fields,
                          "caption": caption, "refs": refs})

    events, observation = [], None
    for i, r in enumerate(rows, 1):
        kind = r.get("kind")
        if kind == "team" and r.get("event") in ("input", "completed", "feedback"):
            events.append((i, r))
            continue
        if kind == "observation":
            observation = i
            continue
        if kind != "decision":
            continue
        round_events, events = events, []
        t = r["time_ms"]
        if not start <= t < end:
            continue
        label = r["request"].rsplit("-", 1)[-1]
        decided = max(t + 2 * MIN_MS, battle(r["elapsed"] + offset))
        read = decided - MIN_MS
        step(t, read, f"The observation at {t / 1000:.2f} s reaches the play loop.",
             [f"{trace} row {observation}"], dots=[OBSERVE])
        dots, parts, refs = [["team.play>team"]], [], []
        for j, e in round_events:
            if e["member"] not in who:
                continue
            w = who[e["member"]]
            refs.append(f"{trace} row {j}")
            if e["event"] == "feedback":
                age = e["latency"].get("delay_ms")
                dots.append({"who": w, "path": [f"team.team>{w}"]})
                parts.append(f"the ack goes to {e['decision']}"
                             + (f" (order age {age} ms)" if age is not None else ""))
            elif e["event"] == "completed":
                dots.append({"who": w, "path": ["team.pool>team"]})
                parts.append(f"it collects {e['decision']}")
            else:
                dots.append({"who": w, "path": ["team.team>pool", f"team.pool>{w}"]})
                parts.append(f"it starts {e['decision']}")
        member = r["behavior"].get("member")
        what = (f"{r['behavior']['decision']}'s batch ({orders(len(r['orders']))})" if member
                else "an idle poll (no member's batch)")
        step(read, decided, f"decide on the {t / 1000:.2f} s observation: "
             + "".join(f"{part}; " for part in parts) + f"it returns {what}.",
             refs + [f"{trace} row {i}"], dots=dots)
        for j, e in round_events:  # each call started in this decide: its worker's think and return
            if e["event"] != "input" or e["member"] not in who or e["decision"] not in done:
                continue
            w, (k, c) = who[e["member"]], done[e["decision"]]
            begin, finish = scaled(e, c["started"]), scaled(e, c["completed"])
            if finish - begin > 100:
                step(max(begin, decided), finish, f"{e['decision']} thinks for"
                     f" {c['completed'] - c['started']:.2f} s of WSL time.", [f"{trace} row {k}"],
                     box=f"team.{w}", who=w)
            back = max(finish, decided)
            step(back, back, f"{e['decision']} returns {orders(len(c['orders']))}; it waits in"
                 " the pool for the next decide.", [f"{trace} row {k}"],
                 dots=[{"who": w, "path": [f"team.{w}>pool"]}])
        j, a = acks.get(r["request"], (None, {}))
        if a.get("applied_ms") is not None:
            extra = {"who": who[member]} if member in who else {}
            step(decided, a["applied_ms"],
                 f"Request {label} is applied at {a['applied_ms'] / 1000:.2f} s.",
                 [f"{trace} row {i}", f"{trace} row {j}"], dots=[REQUEST], **extra)
            items.append({"row": "play", "label": label, "from": t, "to": a["applied_ms"],
                          **extra})
            applied_marks.append(a["applied_ms"])
    for decision, call in inputs.items():
        if call["member"] not in who:
            continue
        completed = done.get(decision, (None, None))[1]
        finish = round(scaled(call, completed["completed"])) if completed else None
        sent, applied = carried.get(decision, (None, None))
        last = applied or sent or finish or end
        if call["source_ms"] < end and last > start:
            items.append({"row": who[call["member"]], "label": decision,
                          "input": call["source_ms"], "completed": finish,
                          "sent": sent, "applied": applied})
    steps.sort(key=lambda s: s["at"])
    return {
        "id": "measured",
        "title": f"Measured replay: {episode.parent.name}",
        "variant": "scripted",
        "clock": "battle time",
        "timing": "measured: one recorded episode",
        "source": f"{name} (recorded at {revision}); generated by scripts/diagram_replay.py",
        "drawn": (f"Every step comes from trace rows; observation, request and application times"
                  f" are recorded. A call's think span starts at its view's recorded time and"
                  f" lasts its WSL duration scaled by {slope:.0f} battle ms per WSL second, the"
                  f" slope of a straight-line fit over this window's {len(window)} input events"
                  f" (largest miss {worst:.0f} ms); a decide's end is its row's WSL time mapped"
                  f" by that fit. Spans under {MIN_MS} ms are drawn {MIN_MS} ms long, and no step"
                  f" is drawn before the battle time it follows."),
        "start": start,
        "end": end,
        "speed": 0.25,
        "steps": steps,
        "lanes": {
            "rows": [{"id": "game", "label": "game: applied"},
                     {"id": "play", "label": "play loop: requests"},
                     *({"id": w, "label": f"member {member}"} for member, w in who.items())],
            "items": items,
            "marks": [{"row": "game", "kind": "applied", "at": applied_marks}],
        },
    }


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
